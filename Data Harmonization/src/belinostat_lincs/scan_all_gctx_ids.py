
import h5py

gctx_file = r"D:\AViiD\GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328_2017-03-06.gctx\GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328.gctx"

try:
    with h5py.File(gctx_file, 'r') as f:
        if '0/META/COL/id' in f:
            ids = f['0/META/COL/id'][:]
            # Decode all IDs
            all_ids = [x.decode('utf-8') for x in ids]
            print(f"Total columns: {len(all_ids)}")
            
            # Check for 'CPC' (Belinostat)
            cpc_ids = [s for s in all_ids if 'CPC' in s]
            print(f"Total CPC IDs found: {len(cpc_ids)}")
            if cpc_ids:
                 print(f"Sample CPC IDs: {cpc_ids[:5]}")
                 
            # Check for 'MUC' (Belinostat)
            muc_ids = [s for s in all_ids if 'MUC' in s]
            print(f"Total MUC IDs found: {len(muc_ids)}")
            if muc_ids:
                 print(f"Sample MUC IDs: {muc_ids[:5]}")
            
            # Check for 'LJP' (Motesanib etc)
            ljp_ids = [s for s in all_ids if 'LJP' in s]
            print(f"Total LJP IDs found: {len(ljp_ids)}")
            
            # Specific check for Motesanib sample seen in metadata
            target_sample = "LJP001_BT20_24H_X1:G19" 
            # Note: GCTX format might be different, e.g. LJP001_BT20_24H:G19 (without _X1)
            # Let's check for "LJP001_BT20_24H" and "G19"
            
            matches = [s for s in all_ids if "LJP001_BT20_24H" in s and "G19" in s]
            print(f"Match for Motesanib sample (LJP001_BT20_24H...G19): {matches}")

except Exception as e:
    print(f"Error: {e}")
