# OPAL-OKB — нативное C++ ядро трассировки лучей (pybind11, C++20).
#
# Паритет важнее скорости: MSVC — /O2 /fp:precise (НЕ fast);
# gcc/clang — -O2 и обязательный -ffp-contract=off (запрет FMA-сжатия,
# иначе порядок округлений отличается от Python и паритет 1e-9 ломается).
cmake_minimum_required(VERSION 3.15)
project(opal_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# LTO ВЫКЛЮЧЕН: /GL+/LTCG (pybind11 включает по умолчанию) даёт access
# violation при импорте модуля в процесс, где уже загружен PyQt5 (Qt5/bin
# подменяет msvcp140/vcruntime140) — воспроизводится на MSVC 19.50.
# Потеря ~5% производительности несущественна при ускорении ×30.
set(PYBIND11_LTO OFF CACHE BOOL "" FORCE)
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION OFF CACHE BOOL "" FORCE)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Статический CRT (/MT): расширение не должно зависеть от VCRUNTIME140.dll /
# MSVCP140.dll. Если в процессе уже загружены СТАРЫЕ версии этих DLL
# (например, из PyQt5\Qt5\bin через pytest-qt), биндинг свежего MSVC-кода
# против чужого старого CRT даёт access violation при LoadLibrary.
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded")

pybind11_add_module(_opal_native src/raytrace.cpp)

if(MSVC)
    # Точность паритета важнее скорости: строго /fp:precise
    target_compile_options(_opal_native PRIVATE /O2 /fp:precise /permissive-)
else()
    # -ffp-contract=off: без сжатия a*b+c → fma — побайтовый паритет с Python
    target_compile_options(_opal_native PRIVATE -O2 -ffp-contract=off)
    if(WIN32)
        # .pyd не должен тянуть libstdc++-6.dll / libgcc_s_seh-1.dll из PATH
        target_link_options(_opal_native PRIVATE -static-libgcc -static-libstdc++)
    endif()
endif()

# Имя модуля: _opal_native.pyd (Windows) / _opal_native*.so
set_target_properties(_opal_native PROPERTIES CXX_VISIBILITY_PRESET hidden)
