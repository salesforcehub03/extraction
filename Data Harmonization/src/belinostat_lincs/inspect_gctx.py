
import h5py
import os

gctx_file = r"D:\AViiD\GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328_2017-03-06.gctx\GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328.gctx"

def visit_func(name, node):
    print(name)

try:
    with h5py.File(gctx_file, 'r') as f:
        print("Keys in file:")
        f.visititems(visit_func)
except Exception as e:
    print(f"Error: {e}")

try:
    with h5py.File(gctx_file, 'r') as f:
        if '0/META/COL/id' in f:
            ids = f['0/META/COL/id'][:5]
            print(f"First 5 Column IDs: {[x.decode('utf-8') for x in ids]}")
except Exception as e:
    print(f"Error reading IDs: {e}")
