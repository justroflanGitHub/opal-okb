"""
OPAL-OKB — LBO Library File Reader

Загрузка .LBO файлов — библиотек оптических систем OPAL-PC.

Формат .LBO файла:
  Последовательность записей переменной длины:
  
  Каждая запись:
    [0-1]     uint16 — маркер записи (0x000C)
    [2-13]    12 bytes — имя .OPJ файла (ASCII, padded spaces)
    [14-17]   4 bytes — метаданные (хеш/идентификатор, варьируется)
    [18-21]   uint32 — размер OPJ данных (N)
    [22..22+N] N bytes — бинарные .OPJ данные (парсятся через opj_reader.load_opj)
  
  Следующая запись начинается сразу после OPJ данных предыдущей.
"""
import struct
import os
import sys
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opj_reader import load_opj


RECORD_MARKER = 0x000C


def _find_records(data: bytes) -> List[dict]:
    """
    Найти все записи в .LBO файле.
    Возвращает список: [{'filename', 'meta', 'opj_size', 'opj_offset', 'record_offset'}, ...]
    """
    records = []
    offset = 0
    
    while offset < len(data) - 22:
        # Check for record marker
        marker = struct.unpack_from('<H', data, offset)[0]
        if marker != RECORD_MARKER:
            offset += 1
            continue
        
        # Read filename
        filename_raw = data[offset+2:offset+14]
        filename = filename_raw.decode('ascii', errors='replace').strip().rstrip('\x00')
        
        # Validate: filename must contain .OPJ
        if '.OPJ' not in filename.upper():
            offset += 1
            continue
        
        # Read metadata and OPJ size
        meta = data[offset+14:offset+18]
        opj_size = struct.unpack_from('<I', data, offset+18)[0]
        opj_offset = offset + 22
        
        # Validate OPJ size
        if opj_size < 52 or opj_offset + opj_size > len(data):
            offset += 1
            continue
        
        records.append({
            'filename': filename,
            'meta': meta,
            'opj_size': opj_size,
            'opj_offset': opj_offset,
            'record_offset': offset,
        })
        
        # Jump to next record
        offset = opj_offset + opj_size
    
    return records


def load_lbo(filepath: str) -> List[dict]:
    """
    Загрузить .LBO файл → список систем.
    
    Args:
        filepath: путь к .LBO файлу
        
    Returns:
        Список словарей:
        [{'name': str, 'description': str, 'opj_data': bytes, 'system': OpticalSystem, 
          'filename': str, 'warnings': list}, ...]
    """
    with open(filepath, 'rb') as f:
        data = f.read()
    
    records = _find_records(data)
    systems = []
    
    for rec in records:
        opj_data = data[rec['opj_offset']:rec['opj_offset'] + rec['opj_size']]
        
        # Extract description from OPJ data (offset 0x0C-0x33, 40 bytes, cp866)
        description = ''
        if len(opj_data) > 0x34:
            try:
                description = opj_data[0x0C:0x34].decode('cp866', errors='replace').strip()
                description = description.replace('\x00', '').strip()
            except Exception:
                description = ''
        
        # Parse OPJ data using the existing opj_reader
        system = None
        warnings = []
        
        # Write to temp file and use load_opj
        import tempfile
        tmpfd, tmppath = tempfile.mkstemp(suffix='.OPJ')
        try:
            os.write(tmpfd, opj_data)
            os.close(tmpfd)
            try:
                system, info = load_opj(tmppath)
                warnings = info.get('warnings', [])
            except Exception as e:
                warnings.append(f'OPJ parse error: {e}')
        finally:
            try:
                os.unlink(tmppath)
            except Exception:
                pass
        
        # Use description as name if system name is empty
        name = description if description else rec['filename']
        if system and system.name and system.name.strip():
            name = system.name.strip()
        
        systems.append({
            'name': name,
            'description': description,
            'opj_data': opj_data,
            'system': system,
            'filename': rec['filename'],
            'warnings': warnings,
        })
    
    return systems


def load_lbo_fast(filepath: str) -> List[dict]:
    """
    Быстрая загрузка .LBO без парсинга OPJ (только имена и описания).
    
    Returns:
        Список словарей: [{'name', 'description', 'filename', 'opj_data'}, ...]
        Без поля 'system' — для быстрого отображения списка.
    """
    with open(filepath, 'rb') as f:
        data = f.read()
    
    records = _find_records(data)
    systems = []
    
    for rec in records:
        opj_data = data[rec['opj_offset']:rec['opj_offset'] + rec['opj_size']]
        
        description = ''
        if len(opj_data) > 0x34:
            try:
                description = opj_data[0x0C:0x34].decode('cp866', errors='replace').strip()
                description = description.replace('\x00', '').strip()
            except Exception:
                description = ''
        
        name = description if description else rec['filename']
        
        systems.append({
            'name': name,
            'description': description,
            'filename': rec['filename'],
            'opj_data': opj_data,
        })
    
    return systems


def get_lbo_info(filepath: str) -> dict:
    """
    Получить информацию о .LBO файле без полной загрузки.
    
    Returns:
        {'path', 'name', 'size', 'num_systems'}
    """
    size = os.path.getsize(filepath)
    name = os.path.splitext(os.path.basename(filepath))[0]
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    records = _find_records(data)
    
    return {
        'path': filepath,
        'name': name,
        'size': size,
        'num_systems': len(records),
    }


def scan_lbo_directory(lib_dir: str) -> List[dict]:
    """
    Сканировать директорию с .LBO файлами.
    
    Returns:
        Список: [{'path', 'name', 'size', 'num_systems'}, ...]
    """
    result = []
    if not os.path.isdir(lib_dir):
        return result
    
    for fname in sorted(os.listdir(lib_dir)):
        if fname.upper().endswith('.LBO'):
            filepath = os.path.join(lib_dir, fname)
            try:
                info = get_lbo_info(filepath)
                result.append(info)
            except Exception:
                result.append({
                    'path': filepath,
                    'name': os.path.splitext(fname)[0],
                    'size': os.path.getsize(filepath),
                    'num_systems': 0,
                })
    
    return result


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    lib_dir = os.path.join(os.path.dirname(__file__), 'extracted', 'opal_okb', 'Lib')
    
    # Scan all LBO files
    lbo_files = scan_lbo_directory(lib_dir)
    print(f"Found {len(lbo_files)} LBO files:\n")
    
    total_systems = 0
    for info in lbo_files:
        print(f"  {info['name']:<12} {info['num_systems']:>4} systems  ({info['size']:>7} bytes)")
        total_systems += info['num_systems']
    
    print(f"\nTotal: {total_systems} systems in {len(lbo_files)} libraries")
    
    # Detailed view of LENS.LBO
    lens_path = os.path.join(lib_dir, 'LENS.LBO')
    print(f"\n=== LENS.LBO detailed ===")
    systems = load_lbo(lens_path)
    print(f"Loaded {len(systems)} systems:\n")
    
    for i, s in enumerate(systems[:10]):
        ns = len(s['system'].surfaces) if s['system'] else 0
        nw = len(s['system'].wavelengths) if s['system'] else 0
        glasses = ','.join(surf.glass for surf in s['system'].surfaces if surf.glass) if s['system'] else ''
        print(f"  [{i:3d}] {s['filename']:<16} {ns}s {nw}w  {s['name'][:45]}")
    
    print(f"  ... ({len(systems)} total)")
