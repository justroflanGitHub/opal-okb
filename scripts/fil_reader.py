"""
OPAL-OKB — FIL (Glass Catalog) Reader
Парсинг бинарных каталогов стёкол из .FIL файлов OPAL-PC
"""
import struct, os, sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def parse_fil_gcn(filepath):
    """
    Парсинг файла каталога стёкол .FIL (формат GCNG = Glass Catalog New)
    
    Структура записи (по документации GLASS.DOC):
    - Марка стекла (8 символов, cp866)
    - Код (4 цифры)
    - Рабочий диапазон длин волн (λ_min, λ_max)
    - Коэффициенты интерполяционной формулы (6 double)
    - nd, vd, ne, ve
    - Плотность
    - Температурные данные
    - Поглощение
    """
    with open(filepath, 'rb') as f:
        data = f.read()
    
    fname = os.path.basename(filepath)
    print(f"Парсинг: {fname} ({len(data)} байт)")
    
    entries = []
    
    # Попробуем найти структуру записей
    # Запись должна содержать строку имени + код + doubles
    # Размер записи попробуем определить из filesize / N
    
    # Сначала найдём все строки, похожие на марки стёкол
    i = 0
    while i < len(data) - 10:
        # Марка стекла: заглавные латинские + цифры + дефис, 6-8 символов
        if (0x41 <= data[i] <= 0x5A) or (0x30 <= data[i] <= 0x39):  # A-Z or 0-9
            start = i
            end = i
            while end < len(data) and end - start < 10:
                b = data[end]
                if (0x41 <= b <= 0x5A) or (0x61 <= b <= 0x7A) or (0x30 <= b <= 0x39) or b == 0x2D or b == 0x20:
                    end += 1
                else:
                    break
            name = data[start:end].decode('ascii', errors='replace').strip()
            if 2 <= len(name) <= 8 and not name.replace('-','').replace(' ','').isdigit():
                # Попробуем прочитать данные после имени
                # Формат: [name 8B] [code 2B] ... [6 doubles] ...
                offset = end
                # Пропускаем нули/пробелы до данных
                while offset < len(data) and (data[offset] == 0 or data[offset] == 0x20):
                    offset += 1
                
                # Читаем doubles после имени
                if offset + 48 <= len(data):
                    doubles = []
                    for j in range(6):
                        if offset + j*8 + 8 <= len(data):
                            try:
                                v = struct.unpack_from('<d', data, offset + j*8)[0]
                                doubles.append(v)
                            except:
                                doubles.append(None)
                    
                    # Проверяем: первые коэффициенты должны быть ~1.5 (показатель преломления)
                    if doubles and doubles[0] is not None and 1.3 < doubles[0] < 2.5:
                        entries.append({
                            'name': name,
                            'offset': start,
                            'coeffs': doubles,
                            'C0': doubles[0] if len(doubles) > 0 else None,
                        })
        i += 1
    
    # Альтернативный подход: фиксированный размер записи
    if not entries:
        # Попробуем шаг 48, 56, 64, 72, 80, 88, 96, 104, 112, 128
        for record_size in [48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 160, 176, 192, 208]:
            if len(data) % record_size != 0:
                continue
            
            n_records = len(data) // record_size
            if n_records < 5 or n_records > 500:
                continue
            
            # Проверим первые несколько записей
            test_entries = []
            for j in range(min(3, n_records)):
                rec_start = j * record_size
                rec = data[rec_start:rec_start + record_size]
                
                # Ищем строку в начале записи
                name_end = 0
                while name_end < min(10, len(rec)) and rec[name_end] >= 0x20:
                    name_end += 1
                name = rec[:name_end].decode('ascii', errors='replace').strip()
                
                # Ищем doubles в записи
                rec_doubles = []
                for k in range(0, len(rec) - 7, 8):
                    v = struct.unpack_from('<d', rec, k)[0]
                    if 0.5 < v < 100:
                        rec_doubles.append((k, v))
                
                if name and len(name) >= 2:
                    test_entries.append((name, rec_doubles))
            
            if len(test_entries) >= 2:
                print(f"  Возможный формат: {n_records} записей по {record_size} байт")
                for name, dbls in test_entries:
                    print(f"    '{name}': {len(dbls)} doubles")
                    for off, v in dbls[:8]:
                        print(f"      @{off}: {v:.6f}")
    
    print(f"  Найдено записей (метод 1): {len(entries)}")
    if entries:
        for e in entries[:20]:
            print(f"    {e['name']:>10} C0={e['C0']:.6f}" if e['C0'] else f"    {e['name']:>10}")
    
    return entries


def parse_all_fil(directory):
    """Парсинг всех .FIL файлов."""
    fil_files = sorted([f for f in os.listdir(directory) if f.upper().endswith('.FIL')])
    
    print(f"Найдено {len(fil_files)} .FIL файлов:\n")
    for f in fil_files:
        path = os.path.join(directory, f)
        parse_fil_gcn(path)
        print()


if __name__ == "__main__":
    opal_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'
    parse_all_fil(opal_dir)
