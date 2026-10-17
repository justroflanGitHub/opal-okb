// OPAL-OKB — нативное C++ ядро трассировки лучей (pybind11).
//
// ЕДИНАЯ реализация физики (пересечения/Снеллиус/OPL): формулы и порядок
// операций ПО БАЙТОВО повторяют референс analysis/ray_tracing.py
// (intersect_sphere / intersect_aspheric / surface_normal / refract /
// trace_ray_through_system), координатные изломы — domain/spatial.py
// (матрицы приходит из Python посчитанными, поэтому в C++ нет тригонометрии).
//
// Показатели преломления Python считает заранее (glass_catalog, включая
// n_override) и передаёт в SurfaceData — дисперсия тут не дублируется.
//
// Сборка: MSVC /O2 /fp:precise; gcc/clang -O2 -ffp-contract=off
// (запрет FMA-сжатия — иначе паритет 1e-9 с Python не гарантируется).

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <array>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <type_traits>
#include <vector>

#ifdef _WIN32
#include <windows.h>  // GetModuleHandleW/GetProcAddress — см. g_pow ниже
#endif

namespace py = pybind11;

// ==== Константы (источник — utils/optics_utils.py, НЕ магические числа) ====
constexpr double EPSILON = 1e-10;  // optics_utils.EPSILON — общий «почти ноль»
constexpr double TINY    = 1e-15;  // optics_utils.TINY — защита деления
// analysis.ray_tracing.TERMINAL_EXIT_EPS — терминальный сегмент при
// нулевой терминальной толщине (GFIX P2; досье REVERSE_GVERIFY §4.1)
constexpr double TERMINAL_EXIT_EPS = 1e-3;
// analysis/ray_tracing.py (skip виртуальной поверхности): порог 1e-6
constexpr double VIRTUAL_SURFACE_TOL = 1e-6;
// intersect_aspheric: max_iter=20, tol=EPSILON (значения по умолчанию референса)
constexpr int NEWTON_MAX_ITER = 20;

// Квадрат ЧЕРЕЗ pow — так делает референс: Python `x ** 2` (CPython
// float_pow) вызывает C pow(x, 2.0), а ucrt pow может отличаться от x*x
// на 1 ulp (замерено: pow(az,2)=…e2823e, az*az=…e2823f — расходится и
// ломает побайтовый паритет). MSVC /fp:precise НЕ сворачивает pow(x,2.0)
// в x*x — проверено пробником на MSVC 19.50.
//
// ВАЖНО (Windows): наш модуль собран со СТАТИЧЕСКИМ CRT (/MT — см.
// native/CMakeLists.txt: сожительство со старыми msvcp140/vcruntime140
// из PyQt5/Qt5), а СТАТИЧЕСКИЙ libucrt pow(x,2) даёт …e2823f (как x*x).
// CPython же зовёт pow из системной ucrtbase.dll → …e2823e. Поэтому все
// pow идут через указатель g_pow на ucrtbase!pow (инициализация в
// PYBIND11_MODULE). На прочих платформах — свой std::pow (glibc pow
// корректно округлён, CPython там зовёт его же).
static double (__cdecl *g_pow)(double, double) = nullptr;

static void init_ref_pow() {
#ifdef _WIN32
    HMODULE h = GetModuleHandleW(L"ucrtbase.dll");  // уже загружена интерпретатором
    if (h)
        g_pow = reinterpret_cast<decltype(g_pow)>(GetProcAddress(h, "pow"));
#endif
}

// pow, побитово совпадающий с CPython float ** (двойное подчёркивание).
static inline double ref_pow(double x, double y) {
    return g_pow ? g_pow(x, y) : std::pow(x, y);
}

static inline double pow2(double x) { return ref_pow(x, 2.0); }

// ==== Коды ошибок — согласованы со строками TraceResult.error в Python ====
// 0=OK, 1=TIR, 2=MISS, 3=EDGE; 4=STOP — обрезка апертурной диафрагмой
// (['_check_aperture_stop' → 'STOP'); строка 'OBSCURED' живёт на уровне
// генерации лучей и в трассировку не попадает).
enum class TraceErr : int32_t { OK = 0, TIR = 1, MISS = 2, EDGE = 3, STOP = 4 };

constexpr int MAX_ASPHERIC_TERMS = 8;  // k2..k10 с запасом: A4..A18

// ==== Данные одной поверхности (POD; заполняется ray_native.prepare_surfaces) ====
struct SurfaceData {
    // -- геометрия (все double идут первыми — без padding) --
    double R;             // радиус кривизны (мм), 0 = плоскость (сырой, как s.radius)
    double z_surf;        // z вершины в глобальной СК (накопление толщин, мм)
    double conic_k;       // коническая постоянная
    double coeffs[MAX_ASPHERIC_TERMS];  // A4, A6, .. — coeffs[j] ↔ r^{2(j+2)}
    double n_before;      // показатель ПЕРЕД поверхностью (среда i-1, для wl)
    double n_after;       // показатель ПОСЛЕ (стекло поверхности, для wl)
    double semi_diameter; // ЭФФЕКТИВНЫЙ полудиаметр (_compute_semi_diameter, Python)
    double cb_m[9];       // R = Rz·Ry·Rx, row-major (domain.spatial.rotation_matrix)
    double cb_dx;         // децентрировка вершины X (мм); z-вершина == z_surf
    double cb_dy;         // децентрировка вершины Y (мм)
    double cb_tilt[3];    // αx, αy, αz (градусы) — справочно; расчёт идёт через cb_m
    // -- флаги (в конце) --
    int32_t num_coeffs;     // len(aspheric_coeffs), используется первые num_coeffs
    int32_t is_aspheric;    // surface_type != SPHERE || |conic|>TINY || coeffs>0
    int32_t is_coord_break; // !CoordBreak.is_identity
    int32_t is_mirror;      // s.is_reflective
    int32_t is_stop;        // индекс поверхности == sys.stop_surface (справочно)
};
static_assert(std::is_standard_layout_v<SurfaceData>,
              "SurfaceData должен быть standard-layout (offsetof в py_surface_dtype)");
static_assert(offsetof(SurfaceData, num_coeffs) == 28 * sizeof(double),
              "SurfaceData: 28 double без padding перед блоком int32");

// Состояние луча: точка (x,y,z) + единичное направление (k,l,m).
struct RayState {
    double x, y, z, k, l, m;
};

// ==== Пересечение со сферой — точная копия intersect_sphere ====
// Возвращает false ⇔ Python None. Выход (hx,hy,hz,t_out) ⇔ кортеж (x,y,z,t).
static inline bool intersect_sphere(const RayState& ray, double R, double z_surf,
                                    double& hx, double& hy, double& hz, double& t_out) {
    if (std::fabs(R) < EPSILON) {
        // Плоская поверхность
        if (std::fabs(ray.m) < TINY) return false;
        double t = (z_surf - ray.z) / ray.m;
        hx = ray.x + t * ray.k;
        hy = ray.y + t * ray.l;
        hz = z_surf;
        t_out = t;
        return true;
    }

    // Сфера с центром в (0, 0, z_surf + R)
    const double cx = 0.0, cy = 0.0, cz = z_surf + R;
    const double dx = ray.x - cx;
    const double dy = ray.y - cy;
    const double dz = ray.z - cz;

    const double a = pow2(ray.k) + pow2(ray.l) + pow2(ray.m);  // =1 для единичного
    const double b = 2.0 * (dx * ray.k + dy * ray.l + dz * ray.m);
    const double c = pow2(dx) + pow2(dy) + pow2(dz) - pow2(R);

    const double disc = pow2(b) - 4.0 * a * c;
    if (disc < 0.0) return false;

    const double sqrt_disc = std::sqrt(disc);
    const double t1 = (-b - sqrt_disc) / (2.0 * a);
    const double t2 = (-b + sqrt_disc) / (2.0 * a);

    // - луч внутри сферы (c < 0): берём t2 (выход)
    // - снаружи: из положительных корней тот, чья точка ближе к вершине
    //   поверхности по z (глубокая вогнутая сфера: ближайший t протыкает
    //   «заднюю» оболочку математической сферы, физический cap — у вершины;
    //   GFIX P6, паритет с analysis/ray_tracing.py)
    double t = -1.0;
    if (c < 0.0) {
        t = t2;
    } else {
        const double tc[2] = {t1, t2};
        double best_dz = 0.0;
        for (int i = 0; i < 2; ++i) {
            if (tc[i] <= EPSILON) continue;
            const double dz_i = std::fabs(ray.z + tc[i] * ray.m - z_surf);
            if (t < 0.0 || dz_i < best_dz) {
                t = tc[i];
                best_dz = dz_i;
            }
        }
    }
    if (t < EPSILON) return false;

    hx = ray.x + t * ray.k;
    hy = ray.y + t * ray.l;
    hz = ray.z + t * ray.m;
    t_out = t;
    return true;
}

// ==== Пересечение с асферикой — Ньютон, точная копия intersect_aspheric ====
// Уравнение: z(r) = c·r²/(1+√(1-(1+k)c²r²)) + Σ A_{2(j+2)}·r^{2(j+2)}, c = 1/R.
// Замечание о паритете: z_asph в НАЧАЛЕ итерации референс вычисляет, но не
// использует (dt берёт z из прошлого снапа) — мёртвый код, здесь опущен.
static inline bool intersect_aspheric(const RayState& ray, double R, double z_surf,
                                      double conic_k, const double* coeffs, int n_coeffs,
                                      double& hx, double& hy, double& hz, double& t_out) {
    // Чистая сфера — быстрый аналитический метод
    if (std::fabs(conic_k) < TINY && n_coeffs == 0)
        return intersect_sphere(ray, R, z_surf, hx, hy, hz, t_out);

    // c = 1/R; для плоскости c = 0
    const double c = (std::fabs(R) > EPSILON) ? 1.0 / R : 0.0;

    // Начальное приближение: базовая сфера (или плоскость)
    double x, y, z, t_init;
    if (!intersect_sphere(ray, R, z_surf, x, y, z, t_init)) return false;

    for (int iter = 0; iter < NEWTON_MAX_ITER; ++iter) {
        double r_sq = x * x + y * y;
        double r = (r_sq > 0.0) ? std::sqrt(r_sq) : 0.0;

        // dz/dr: коническая часть
        double dz_dr = 0.0;
        if (std::fabs(c) > TINY && r > TINY) {
            double k1c_sq = (1.0 + conic_k) * c * c;
            double disc = 1.0 - k1c_sq * r_sq;
            if (disc < TINY) disc = TINY;
            const double sqrt_disc = std::sqrt(disc);
            dz_dr = c * r / sqrt_disc;
        }
        // dz/dr: полином d/dr[A₄r⁴+..] = 4A₄r³ + 6A₆r⁵ + ...
        for (int j = 0; j < n_coeffs; ++j) {
            const int e = 2 * (j + 2);  // степень r в самом члене: 4, 6, 8, ...
            if (r > TINY)
                dz_dr += coeffs[j] * static_cast<double>(e) * ref_pow(r, static_cast<double>(e - 1));
            else
                dz_dr += 0.0;
        }

        // Нормаль: (-dz/dr·x/r, -dz/dr·y/r, 1), нормализованная
        double nx, ny;
        if (r > TINY) {
            nx = -dz_dr * x / r;
            ny = -dz_dr * y / r;
        } else {
            nx = 0.0;
            ny = 0.0;
        }
        double nz = 1.0;
        const double n_len = std::sqrt(nx * nx + ny * ny + nz * nz);
        if (n_len > TINY) {
            nx /= n_len;
            ny /= n_len;
            nz /= n_len;
        }

        const double dot_nd = nx * ray.k + ny * ray.l + nz * ray.m;
        if (std::fabs(dot_nd) < TINY) break;

        // Корректирующее смещение вдоль луча
        const double dt = (nx * (x - ray.x) + ny * (y - ray.y) + nz * (z - ray.z)) / dot_nd;

        x = x + dt * ray.k;
        y = y + dt * ray.l;
        z = z + dt * ray.m;

        // Пересчёт z_asph для новых x,y и snap z к поверхности
        r_sq = x * x + y * y;
        r = (r_sq > 0.0) ? std::sqrt(r_sq) : 0.0;
        double z_asph_new = z_surf;
        if (std::fabs(c) > TINY && r_sq > 0.0) {
            double k1c_sq = (1.0 + conic_k) * c * c;
            double disc = 1.0 - k1c_sq * r_sq;
            if (disc < 0.0) disc = 0.0;
            z_asph_new += c * r_sq / (1.0 + std::sqrt(disc));
        }
        const double r2 = r_sq;
        for (int j = 0; j < n_coeffs; ++j) {
            const int power = 2 * (j + 2);  // A4->r⁴, A6->r⁶, ...
            // Python: r2 ** (power // 2) — именно pow от r² (не r^power!)
            z_asph_new += coeffs[j] * ref_pow(r2, static_cast<double>(power / 2));
        }
        z = z_asph_new;

        if (std::fabs(dt) < EPSILON) break;
    }

    const double t = std::sqrt(pow2(x - ray.x) + pow2(y - ray.y) + pow2(z - ray.z));
    if (t < EPSILON) return false;

    hx = x;
    hy = y;
    hz = z;
    t_out = t;
    return true;
}

// ==== Нормаль к сфере — точная копия surface_normal ====
static inline void surface_normal_sphere(double x, double y, double z, double R, double z_surf,
                                         double& nx, double& ny, double& nz) {
    if (std::fabs(R) < EPSILON) {
        nx = 0.0;
        ny = 0.0;
        nz = 1.0;
        return;
    }
    const double cx = 0.0, cy = 0.0, cz = z_surf + R;
    const double ax = x - cx;
    const double ay = y - cy;
    const double az = z - cz;
    const double norm = std::sqrt(pow2(ax) + pow2(ay) + pow2(az));
    if (norm < TINY) {
        nx = 0.0;
        ny = 0.0;
        nz = 1.0;
        return;
    }
    nx = ax / norm;
    ny = ay / norm;
    nz = az / norm;
}

// ==== Нормаль к асферике — точная копия surface_normal_aspheric ====
static inline void surface_normal_aspheric(double x, double y, double z, double R, double z_surf,
                                           double conic_k, const double* coeffs, int n_coeffs,
                                           double& nx, double& ny, double& nz) {
    if (std::fabs(conic_k) < TINY && n_coeffs == 0)
        return surface_normal_sphere(x, y, z, R, z_surf, nx, ny, nz);

    const double c = (std::fabs(R) > EPSILON) ? 1.0 / R : 0.0;
    const double r_sq = x * x + y * y;
    const double r = (r_sq > 0.0) ? std::sqrt(r_sq) : 0.0;

    double dz_dr = 0.0;
    if (std::fabs(c) > TINY && r > TINY) {
        double k1c_sq = (1.0 + conic_k) * c * c;
        double disc = 1.0 - k1c_sq * r_sq;
        if (disc < TINY) disc = TINY;
        dz_dr = c * r / std::sqrt(disc);
    }
    for (int j = 0; j < n_coeffs; ++j) {
        const int e = 2 * (j + 2);
        if (r > TINY)
            dz_dr += coeffs[j] * static_cast<double>(e) * ref_pow(r, static_cast<double>(e - 1));
    }

    double ax, ay;
    if (r > TINY) {
        ax = -dz_dr * x / r;
        ay = -dz_dr * y / r;
    } else {
        ax = 0.0;
        ay = 0.0;
    }
    const double az = 1.0;
    const double n_len = std::sqrt(ax * ax + ay * ay + az * az);
    if (n_len > TINY) {
        nx = ax / n_len;
        ny = ay / n_len;
        nz = az / n_len;
        return;
    }
    nx = 0.0;
    ny = 0.0;
    nz = 1.0;
}

// ==== Снеллиус в векторной форме — точная копия refract ====
// Возвращает false ⇔ TIR.
static inline bool refract(double k, double l, double m, double nx, double ny, double nz,
                           double n1, double n2,
                           double& k_new, double& l_new, double& m_new) {
    double cos_i = -(k * nx + l * ny + m * nz);
    if (cos_i < 0.0) {
        // Нормаль направлена неправильно
        nx = -nx;
        ny = -ny;
        nz = -nz;
        cos_i = -cos_i;
    }

    const double eta = n1 / n2;
    const double sin2_t = pow2(eta) * (1.0 - pow2(cos_i));
    if (sin2_t > 1.0) return false;  // TIR

    const double cos_t = std::sqrt(1.0 - sin2_t);

    const double kn = eta * k + (eta * cos_i - cos_t) * nx;
    const double ln = eta * l + (eta * cos_i - cos_t) * ny;
    const double mn = eta * m + (eta * cos_i - cos_t) * nz;

    const double norm = std::sqrt(pow2(kn) + pow2(ln) + pow2(mn));
    k_new = kn / norm;
    l_new = ln / norm;
    m_new = mn / norm;
    return true;
}

// ==== Координатный излом (domain/spatial.py; матрицы уже посчитаны в Python) ====
// p_local = Rᵀ·(p − V), V = (cb_dx, cb_dy, z_surf) — CoordBreak.point_to_local
static inline void point_to_local(const SurfaceData& s, double px, double py, double pz,
                                  double& ox, double& oy, double& oz) {
    const double sx = px - s.cb_dx;
    const double sy = py - s.cb_dy;
    const double sz = pz - s.z_surf;
    const double* m = s.cb_m;  // row-major
    ox = m[0] * sx + m[3] * sy + m[6] * sz;  // mat_tvec: mᵀ·v
    oy = m[1] * sx + m[4] * sy + m[7] * sz;
    oz = m[2] * sx + m[5] * sy + m[8] * sz;
}

// p_global = V + R·p_local — CoordBreak.point_to_global
static inline void point_to_global(const SurfaceData& s, double px, double py, double pz,
                                   double& ox, double& oy, double& oz) {
    const double* m = s.cb_m;
    const double rx = m[0] * px + m[1] * py + m[2] * pz;  // mat_vec: m·v
    const double ry = m[3] * px + m[4] * py + m[5] * pz;
    const double rz = m[6] * px + m[7] * py + m[8] * pz;
    ox = rx + s.cb_dx;
    oy = ry + s.cb_dy;
    oz = rz + s.z_surf;
}

// d_local = Rᵀ·d — CoordBreak.dir_to_local
static inline void dir_to_local(const SurfaceData& s, double k, double l, double m,
                                double& ok_, double& ol_, double& om_) {
    const double* mm = s.cb_m;
    ok_ = mm[0] * k + mm[3] * l + mm[6] * m;
    ol_ = mm[1] * k + mm[4] * l + mm[7] * m;
    om_ = mm[2] * k + mm[5] * l + mm[8] * m;
}

// d_global = R·d — CoordBreak.dir_to_global
static inline void dir_to_global(const SurfaceData& s, double k, double l, double m,
                                 double& ok_, double& ol_, double& om_) {
    const double* mm = s.cb_m;
    ok_ = mm[0] * k + mm[1] * l + mm[2] * m;
    ol_ = mm[3] * k + mm[4] * l + mm[5] * m;
    om_ = mm[6] * k + mm[7] * l + mm[8] * m;
}

// ==== Результат трассировки одного луча ====
struct TraceOut {
    std::vector<double> path_x, path_y, path_z;  // точки пути (глобальная СК)
    double fin[6] = {0, 0, 0, 0, 0, 0};          // финальное состояние луча
    double opl = 0.0;
    int32_t surfaces_hit = 0;
    TraceErr err = TraceErr::OK;

    inline void add_point(double x, double y, double z) {
        path_x.push_back(x);
        path_y.push_back(y);
        path_z.push_back(z);
    }
};

// ==== Трассировка одного луча — точная копия trace_ray_through_system ====
// Системные величины (z_stop/stop_radius/показатели/вершины) Python вычисляет
// заранее: преамбула референса не имеет побочных эффектов на луч.
static void trace_one_core(const SurfaceData* surfaces, int32_t n_surf,
                           double x0, double y0, double z0,
                           double k0, double l0, double m0,
                           bool has_stop, double z_stop, double stop_radius,
                           double n_start, bool propagate_to_image, double img_z,
                           TraceOut& out) {
    out.add_point(x0, y0, z0);

    double cur_x = x0, cur_y = y0, cur_z = z0;
    double cur_k = k0, cur_l = l0, cur_m = m0;
    double current_n = n_start;  // n среды перед системой
    int32_t surfaces_hit = 0;
    double opl = 0.0;

    for (int32_t i = 0; i < n_surf; ++i) {
        const SurfaceData& s = surfaces[i];
        const double z_surf = s.z_surf;

        // -- апертурная диафрагма: если она между лучом и следующей поверхностью --
        if (has_stop && z_stop > cur_z + EPSILON && z_stop < z_surf - EPSILON &&
            !(std::fabs(cur_m) < TINY)) {
            const double dt_stop = (z_stop - cur_z) / cur_m;
            const double sx = cur_x + dt_stop * cur_k;
            const double sy = cur_y + dt_stop * cur_l;
            const double r_at_stop = std::sqrt(pow2(sx) + pow2(sy));

            if (stop_radius > 0 && r_at_stop > stop_radius) {
                // Луч обрезан диафрагмой
                out.add_point(sx, sy, z_stop);
                opl += current_n * dt_stop;
                out.err = TraceErr::STOP;
                goto finish;
            }
            // Луч прошёл диафрагму — добавим точку
            out.add_point(sx, sy, z_stop);
            opl += current_n * dt_stop;
            cur_x = sx;
            cur_y = sy;
            cur_z = z_stop;
        }

        // -- локальная СК поверхности (наклон/децентрировка, п. 17) --
        RayState local_ray;
        double z_intersect;
        if (!s.is_coord_break) {
            local_ray.x = cur_x; local_ray.y = cur_y; local_ray.z = cur_z;
            local_ray.k = cur_k; local_ray.l = cur_l; local_ray.m = cur_m;
            z_intersect = z_surf;  // быстрый путь
        } else {
            point_to_local(s, cur_x, cur_y, cur_z, local_ray.x, local_ray.y, local_ray.z);
            dir_to_local(s, cur_k, cur_l, cur_m, local_ray.k, local_ray.l, local_ray.m);
            z_intersect = 0.0;  // вершина — в начале локальной СК
        }

        const double R = (std::fabs(s.R) > EPSILON) ? s.R : 0.0;

        // -- пересечение --
        double hx, hy, hz, t;
        bool hit;
        if (s.is_aspheric) {
            hit = intersect_aspheric(local_ray, R, z_intersect, s.conic_k,
                                     s.coeffs, s.num_coeffs, hx, hy, hz, t);
        } else {
            hit = intersect_sphere(local_ray, R, z_intersect, hx, hy, hz, t);
        }
        // NaN-безопасность: луч мимо поверхности или расхождение итераций
        if (!hit || !(std::isfinite(hx) && std::isfinite(hy) &&
                      std::isfinite(hz) && std::isfinite(t))) {
            // Виртуальная поверхность (позади луча) — пропустить, продолжить трассу
            const bool going_forward = local_ray.m > 0;
            const bool surface_behind = going_forward
                ? (z_intersect < local_ray.z - VIRTUAL_SURFACE_TOL)
                : (z_intersect > local_ray.z + VIRTUAL_SURFACE_TOL);
            if (surface_behind) continue;

            out.err = TraceErr::MISS;
            goto finish;
        }

        // -- полудиаметр (в локальной СК), точка — в глобальной --
        const double r_hit = std::sqrt(pow2(hx) + pow2(hy));
        double gx, gy, gz;
        if (!s.is_coord_break) {
            gx = hx; gy = hy; gz = hz;
        } else {
            point_to_global(s, hx, hy, hz, gx, gy, gz);
        }
        if (r_hit > s.semi_diameter) {
            out.err = TraceErr::EDGE;
            out.add_point(gx, gy, gz);
            opl += current_n * t;
            goto finish;
        }

        // -- физический cap (GFIX P6): в апертуре действует оболочка у
        // ВЕРШИНЫ (стрела прогиба на semi_d); «спина» математической сферы
        // (|hz−z_surf| ≈ 2|R|−sag) — не поверхность (Кассегрен с
        // инвертированной толщиной, MISS-диагностика) --
        if (!s.is_aspheric && R != 0.0) {
            const double a_cap = std::fmin(s.semi_diameter, std::fabs(R));
            const double sag = std::fabs(R) - std::sqrt(R * R - a_cap * a_cap);
            if (std::fabs(hz - z_intersect) > sag + 1e-6) {
                out.err = TraceErr::MISS;
                goto finish;
            }
        }

        // -- OPL: n * геометрическое расстояние --
        opl += current_n * t;
        out.add_point(gx, gy, gz);
        surfaces_hit += 1;

        // -- нормаль (в локальной СК) --
        double nx, ny, nz;
        if (s.is_aspheric) {
            surface_normal_aspheric(hx, hy, hz, R, z_intersect, s.conic_k,
                                    s.coeffs, s.num_coeffs, nx, ny, nz);
        } else {
            surface_normal_sphere(hx, hy, hz, R, z_intersect, nx, ny, nz);
        }

        // -- преломление/отражение (n уже посчитаны для этой λ) --
        const double n1 = s.n_before;
        const double n2 = s.n_after;
        current_n = n2;
        if (s.is_mirror) {
            // Отражение: среда не меняется
            current_n = n1;
            const double dot = local_ray.k * nx + local_ray.l * ny + local_ray.m * nz;
            local_ray.k = local_ray.k - 2.0 * dot * nx;
            local_ray.l = local_ray.l - 2.0 * dot * ny;
            local_ray.m = local_ray.m - 2.0 * dot * nz;
        } else {
            double nk, nl, nm;
            if (!refract(local_ray.k, local_ray.l, local_ray.m, nx, ny, nz, n1, n2, nk, nl, nm)) {
                out.err = TraceErr::TIR;
                goto finish;
            }
            local_ray.k = nk;
            local_ray.l = nl;
            local_ray.m = nm;
        }

        // -- назад в глобальную СК --
        cur_x = gx;
        cur_y = gy;
        cur_z = gz;
        if (!s.is_coord_break) {
            cur_k = local_ray.k;
            cur_l = local_ray.l;
            cur_m = local_ray.m;
        } else {
            dir_to_global(s, local_ray.k, local_ray.l, local_ray.m, cur_k, cur_l, cur_m);
        }
    }

    // -- после последней поверхности — до плоскости изображения --
    if (n_surf > 0 && propagate_to_image && !(std::fabs(cur_m) < TINY)) {
        // Нулевая терминальная толщина: плоскость изображения совпадает с
        // вершиной последней поверхности — терминальный сегмент строится
        // длиной TERMINAL_EXIT_EPS ПО ХОДУ луча (знак по cur_m; паритет с
        // Python-трейсером, GFIX P2): путь всегда кончается сегментом с
        // пост-рефракционным направлением, сегмент не вырождается.
        double target = img_z;
        if (std::fabs(target - surfaces[n_surf - 1].z_surf) < TINY) {
            target += (cur_m > 0.0) ? TERMINAL_EXIT_EPS : -TERMINAL_EXIT_EPS;
        }
        const double dt = (target - cur_z) / cur_m;
        const double ix = cur_x + dt * cur_k;
        const double iy = cur_y + dt * cur_l;
        opl += current_n * dt;
        out.add_point(ix, iy, target);
    }

finish:
    out.fin[0] = cur_x; out.fin[1] = cur_y; out.fin[2] = cur_z;
    out.fin[3] = cur_k; out.fin[4] = cur_l; out.fin[5] = cur_m;
    out.opl = opl;
    out.surfaces_hit = surfaces_hit;
}

// ==== Проверка массива поверхностей (dtype собран самим модулем) ====
static const SurfaceData* check_surfaces(py::handle obj) {
    py::array arr = py::array::ensure(obj, py::array::c_style);
    if (arr.ndim() != 1)
        throw py::value_error("surfaces: ожидается 1-D массив структур SurfaceData");
    if (arr.dtype().kind() != 'V')
        throw py::value_error("surfaces: ожидается structured dtype из surface_dtype()");
    if (arr.itemsize() != static_cast<int>(sizeof(SurfaceData)))
        throw py::value_error("surfaces: itemsize не совпадает с SurfaceData — собери dtype через surface_dtype()");
    if (arr.nbytes() == 0)
        throw py::value_error("surfaces: пустая система");
    return static_cast<const SurfaceData*>(arr.data());
}

// ==== Python-обёртка: одиночный луч (паритет/отладка) ====
static py::dict py_trace_one(py::array surfaces, std::array<double, 6> ray, double wl,
                             bool has_stop, double z_stop, double stop_radius,
                             double n_start, bool propagate_to_image, double img_z) {
    (void)wl;  // показатели уже посчитаны в prepare_surfaces для этой λ
    const SurfaceData* sd = check_surfaces(surfaces);
    TraceOut out;
    trace_one_core(sd, static_cast<int32_t>(surfaces.shape(0)),
                   ray[0], ray[1], ray[2], ray[3], ray[4], ray[5],
                   has_stop, z_stop, stop_radius, n_start, propagate_to_image, img_z, out);

    py::list path;
    for (size_t j = 0; j < out.path_x.size(); ++j)
        path.append(py::make_tuple(out.path_x[j], out.path_y[j], out.path_z[j]));
    py::dict res;
    res["path"] = path;
    res["success"] = (out.err == TraceErr::OK);
    res["error_code"] = static_cast<int>(out.err);
    res["surfaces_hit"] = out.surfaces_hit;
    res["opl"] = out.opl;
    res["end_ray"] = py::make_tuple(out.fin[0], out.fin[1], out.fin[2],
                                    out.fin[3], out.fin[4], out.fin[5]);
    return res;
}

// ==== Python-обёртка: батч (N × 6) ====
static py::dict py_trace_batch(py::array surfaces, py::array_t<double, py::array::c_style | py::array::forcecast> rays,
                               double wl, bool has_stop, double z_stop, double stop_radius,
                               double n_start, bool propagate_to_image, double img_z) {
    (void)wl;  // показатели уже посчитаны в prepare_surfaces для этой λ
    const SurfaceData* sd = check_surfaces(surfaces);

    py::buffer_info ri = rays.request();
    if (ri.ndim != 2 || ri.shape[1] != 6)
        throw py::value_error("rays: ожидается массив (N, 6) — x,y,z,k,l,m");
    const py::ssize_t n_rays = ri.shape[0];
    const double* rdata = static_cast<const double*>(ri.ptr);
    const int32_t n_surf = static_cast<int32_t>(surfaces.shape(0));

    std::vector<TraceOut> outs(static_cast<size_t>(n_rays));
    {
        // Чистый C++ на сырых указателях — GIL не нужен
        py::gil_scoped_release nogil;
        for (py::ssize_t i = 0; i < n_rays; ++i) {
            const double* r = rdata + 6 * i;
            trace_one_core(sd, n_surf, r[0], r[1], r[2], r[3], r[4], r[5],
                           has_stop, z_stop, stop_radius, n_start,
                           propagate_to_image, img_z, outs[static_cast<size_t>(i)]);
        }
    }

    // Склейка путей (CSR): path_flat (M,3) + path_offsets (N+1)
    py::ssize_t total_pts = 0;
    for (const TraceOut& o : outs) total_pts += static_cast<py::ssize_t>(o.path_x.size());

    py::array_t<double> path_flat({total_pts, static_cast<py::ssize_t>(3)});
    py::array_t<int32_t> offsets(n_rays + 1);
    py::array_t<double> end_ray({n_rays, static_cast<py::ssize_t>(6)});
    py::array_t<double> opl(n_rays);
    py::array_t<int32_t> err_code(n_rays);
    py::array_t<int32_t> surfaces_hit(n_rays);
    // success как numpy bool (массив uint8 с маской)
    py::array_t<bool> success(n_rays);

    auto pf = path_flat.mutable_unchecked<2>();
    auto off = offsets.mutable_unchecked<1>();
    auto er = end_ray.mutable_unchecked<2>();
    auto op = opl.mutable_unchecked<1>();
    auto ec = err_code.mutable_unchecked<1>();
    auto sh = surfaces_hit.mutable_unchecked<1>();
    auto sc = success.mutable_unchecked<1>();

    py::ssize_t p = 0;
    for (py::ssize_t i = 0; i < n_rays; ++i) {
        const TraceOut& o = outs[static_cast<size_t>(i)];
        off(i) = static_cast<int32_t>(p);
        for (size_t j = 0; j < o.path_x.size(); ++j) {
            pf(p, 0) = o.path_x[j];
            pf(p, 1) = o.path_y[j];
            pf(p, 2) = o.path_z[j];
            ++p;
        }
        for (int c = 0; c < 6; ++c) er(i, c) = o.fin[c];
        op(i) = o.opl;
        ec(i) = static_cast<int32_t>(o.err);
        sh(i) = o.surfaces_hit;
        sc(i) = (o.err == TraceErr::OK);
    }
    off(n_rays) = static_cast<int32_t>(p);

    py::dict res;
    res["path_flat"] = path_flat;
    res["path_offsets"] = offsets;
    res["end_ray"] = end_ray;
    res["opl"] = opl;
    res["error_code"] = err_code;
    res["surfaces_hit"] = surfaces_hit;
    res["success"] = success;
    return res;
}

// ==== Спецификация numpy dtype для SurfaceData (единственный источник) ====
// np.dtype({'names': ..., 'formats': ..., 'offsets': ..., 'itemsize': ...})
static py::dict py_surface_dtype() {
    py::list names, formats, offsets;
    auto add = [&](const char* name, size_t off) {
        names.append(name);
        formats.append("float64");
        offsets.append(off);
    };
    auto addi = [&](const char* name, size_t off) {
        names.append(name);
        formats.append("int32");
        offsets.append(off);
    };
    add("R", offsetof(SurfaceData, R));
    add("z_surf", offsetof(SurfaceData, z_surf));
    add("conic_k", offsetof(SurfaceData, conic_k));
    for (int j = 0; j < MAX_ASPHERIC_TERMS; ++j) {
        char buf[8];
        std::snprintf(buf, sizeof(buf), "c%d", j);
        add(buf, offsetof(SurfaceData, coeffs) + j * sizeof(double));
    }
    add("n_before", offsetof(SurfaceData, n_before));
    add("n_after", offsetof(SurfaceData, n_after));
    add("semi_diameter", offsetof(SurfaceData, semi_diameter));
    for (int j = 0; j < 9; ++j) {
        char buf[8];
        std::snprintf(buf, sizeof(buf), "m%d%d", j / 3, j % 3);
        add(buf, offsetof(SurfaceData, cb_m) + j * sizeof(double));
    }
    add("cb_dx", offsetof(SurfaceData, cb_dx));
    add("cb_dy", offsetof(SurfaceData, cb_dy));
    for (int j = 0; j < 3; ++j) {
        char buf[8];
        std::snprintf(buf, sizeof(buf), "tilt%d", j);
        add(buf, offsetof(SurfaceData, cb_tilt) + j * sizeof(double));
    }
    addi("num_coeffs", offsetof(SurfaceData, num_coeffs));
    addi("is_aspheric", offsetof(SurfaceData, is_aspheric));
    addi("is_coord_break", offsetof(SurfaceData, is_coord_break));
    addi("is_mirror", offsetof(SurfaceData, is_mirror));
    addi("is_stop", offsetof(SurfaceData, is_stop));

    py::dict spec;
    spec["names"] = names;
    spec["formats"] = formats;
    spec["offsets"] = offsets;
    spec["itemsize"] = static_cast<int>(sizeof(SurfaceData));
    return spec;
}

PYBIND11_MODULE(_opal_native, m) {
    m.doc() = "OPAL-OKB: нативное C++ ядро трассировки лучей (паритет analysis/ray_tracing.py)";

    // Привязка pow к ucrtbase.dll ДО любого вызова трассировки (паритет
    // с CPython float ** — см. комментарий у g_pow).
    init_ref_pow();

    // Константы референса (utils/optics_utils.py) — для интроспекции/тестов
    m.attr("EPSILON") = EPSILON;
    m.attr("TINY") = TINY;
    m.attr("VIRTUAL_SURFACE_TOL") = VIRTUAL_SURFACE_TOL;
    m.attr("NEWTON_MAX_ITER") = NEWTON_MAX_ITER;
    m.attr("MAX_ASPHERIC_TERMS") = MAX_ASPHERIC_TERMS;
    m.attr("ERR_OK") = static_cast<int>(TraceErr::OK);
    m.attr("ERR_TIR") = static_cast<int>(TraceErr::TIR);
    m.attr("ERR_MISS") = static_cast<int>(TraceErr::MISS);
    m.attr("ERR_EDGE") = static_cast<int>(TraceErr::EDGE);
    m.attr("ERR_STOP") = static_cast<int>(TraceErr::STOP);

    m.def("surface_dtype", &py_surface_dtype,
          "Спецификация numpy structured dtype для SurfaceData (names/formats/offsets/itemsize).");

    m.def("ref_pow", &ref_pow, py::arg("x"), py::arg("y"),
          "pow, побитово совпадающий с CPython float ** (ucrtbase.dll на Windows); "
          "для самопроверки паритета в тестах.");

    m.def("trace_one", &py_trace_one,
          py::arg("surfaces"), py::arg("ray"), py::arg("wl") = 0.58756,
          py::arg("has_stop") = false, py::arg("z_stop") = 0.0, py::arg("stop_radius") = 0.0,
          py::arg("n_start") = 1.0, py::arg("propagate_to_image") = true, py::arg("img_z") = 0.0,
          "Трассировка одиночного луча (x,y,z,k,l,m); возвращает dict "
          "(path, success, error_code, surfaces_hit, opl, end_ray).");

    m.def("trace_batch", &py_trace_batch,
          py::arg("surfaces"), py::arg("rays"), py::arg("wl") = 0.58756,
          py::arg("has_stop") = false, py::arg("z_stop") = 0.0, py::arg("stop_radius") = 0.0,
          py::arg("n_start") = 1.0, py::arg("propagate_to_image") = true, py::arg("img_z") = 0.0,
          "Батч-трассировка N лучей (N,6); возвращает dict numpy-массивов: "
          "path_flat (M,3), path_offsets (N+1), end_ray (N,6), opl (N), "
          "error_code (N), surfaces_hit (N), success (N).");
}
