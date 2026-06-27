"""Try to use opal_api.dll via ctypes to read an OPJ file."""
import sys, os, ctypes

dll_path = r'C:\Users\mikhail\.openclaw\workspace\opal_ utils\converter\opal_api.dll'
lib_dir = os.path.dirname(dll_path)

# Add DLL directory to path so dependencies (Qt5) can be found
os.add_dll_directory(lib_dir)

try:
    api = ctypes.CDLL(dll_path)
    print(f"Loaded opal_api.dll OK")
except Exception as e:
    print(f"Failed to load: {e}")
    sys.exit(1)

# Try to call functions
# The mangled names are C++ exports. Let's try to find unmangled ones.
# First, let's check what functions exist
import subprocess
result = subprocess.run(['dumpbin', '/exports', dll_path], capture_output=True, text=True)
if result.returncode == 0:
    print("\n=== Exports (dumpbin) ===")
    for line in result.stdout.splitlines():
        if 'OPAL_' in line:
            print(f"  {line.strip()}")
else:
    # Try objdump from mingw if available
    print("dumpbin not available, using ctypes directly")

# The functions use C++ name mangling: ?OPAL_FunctionName@@YA...
# Let's try calling with the mangled names
# But first, let's see if there's a read_opj function
print("\n=== Trying to call API ===")

# Look for OPAL_Read_OPJ or similar
import struct
data = open(dll_path, 'rb').read()
for term in [b'Read_OPJ', b'Open', b'Load', b'read_opj', b'OPAL_Read']:
    pos = data.find(term)
    if pos >= 0:
        ctx = data[max(0,pos-20):pos+40]
        print(f"Found '{term.decode()}' at {pos:#x}: {ctx}")

# Try simple calls - maybe the API works with ordinal exports
# or we can use the mangled names directly

# Let's get function pointers by mangled name
# ?OPAL_Object_Get_Type@@YAHPA_N@Z → returns int, takes bool* 
# ?OPAL_Image_Get_Type@@YAHPA_N@Z

try:
    # These are the C++ mangled names from the export table
    get_obj_type = getattr(api, '?OPAL_Object_Get_Type@@YAHPA_N@Z')
    get_obj_type.restype = ctypes.c_int
    get_obj_type.argtypes = [ctypes.POINTER(ctypes.c_bool)]
    
    get_img_type = getattr(api, '?OPAL_Image_Get_Type@@YAHPA_N@Z')
    get_img_type.restype = ctypes.c_int
    get_img_type.argtypes = [ctypes.POINTER(ctypes.c_bool)]
    
    get_img_dist_type = getattr(api, '?OPAL_Image_Get_Distance_Type@@YAH_N@Z')
    get_img_dist_type.restype = ctypes.c_int
    get_img_dist_type.argtypes = [ctypes.c_bool]
    
    get_obj_size = getattr(api, '?OPAL_Object_Get_Size@@YAHPAN@Z')
    get_obj_size.restype = ctypes.c_int
    get_obj_size.argtypes = [ctypes.POINTER(ctypes.c_double)]
    
    get_img_size = getattr(api, '?OPAL_Image_Get_Size@@YAHPAN@Z')
    get_img_size.restype = ctypes.c_int
    get_img_size.argtypes = [ctypes.POINTER(ctypes.c_double)]
    
    get_img_size_grad = getattr(api, '?OPAL_Image_Get_Size_Grad@@YAHPAN@Z')
    get_img_size_grad.restype = ctypes.c_int
    get_img_size_grad.argtypes = [ctypes.POINTER(ctypes.c_double)]
    
    get_stop_type = getattr(api, '?OPAL_Stop_Get_Type@@YAHPAD@Z')
    get_stop_type.restype = ctypes.c_int
    get_stop_type.argtypes = [ctypes.POINTER(ctypes.c_char)]
    
    get_stop_surf = getattr(api, '?OPAL_Stop_Get_Surface_Num@@YAHPAH@Z')
    get_stop_surf.restype = ctypes.c_int
    get_stop_surf.argtypes = [ctypes.POINTER(ctypes.c_int)]
    
    get_stop_size = getattr(api, '?OPAL_Stop_Get_Size@@YAHPAN@Z')
    get_stop_size.restype = ctypes.c_int
    get_stop_size.argtypes = [ctypes.POINTER(ctypes.c_double)]
    
    get_f = getattr(api, '?OPAL_Paraxial_Get_F@@YAHPAN@Z')
    get_f.restype = ctypes.c_int
    get_f.argtypes = [ctypes.POINTER(ctypes.c_double)]
    
    print("All function pointers resolved OK")
    
except AttributeError as e:
    print(f"Function not found: {e}")
    print("\nTrying to list all exports...")
    # List all symbols
    for name in dir(api):
        if 'OPAL' in name:
            print(f"  {name}")
