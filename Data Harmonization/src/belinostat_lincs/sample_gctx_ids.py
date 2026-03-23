
import h5py
import random

gctx_file = r"D:\AViiD\GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328_2017-03-06.gctx\GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328.gctx"

try:
    with h5py.File(gctx_file, 'r') as f:
        if '0/META/COL/id' in f:
            ids = f['0/META/COL/id'][:]
            total_cols = len(ids)
            print(f"Total columns: {total_cols}")
            
            # Sample 20 random IDs
            indices = sorted(random.sample(range(total_cols), 20))
            sample_ids = [ids[i].decode('utf-8') for i in indices]
            
            print("\nRandom Sample IDs:")
            for s_id in sample_ids:
                print(s_id)
                
            # Check for non-REP IDs
            non_rep = [s for s in sample_ids if not s.startswith('REP')]
            print(f"\nNon-REP IDs in sample: {non_rep}")
            
            # Check for CPC IDs (Belinostat plates)
            cpc_ids = [s for s in sample_ids if s.startswith('CPC')]
            print(f"CPC IDs in sample: {cpc_ids}")
            
            # Scan first 5000 IDs for any CPC
            first_5k = [x.decode('utf-8') for x in ids[:5000]]
            cpc_5k = [s for s in first_5k if s.startswith('CPC')]
            print(f"CPC IDs in first 5000: {len(cpc_5k)}")
            if cpc_5k:
                print(f"Sample CPC: {cpc_5k[0]}")

            # Scan LAST 5000 IDs
            last_5k = [x.decode('utf-8') for x in ids[-5000:]]
            cpc_last = [s for s in last_5k if s.startswith('CPC')]
            print(f"CPC IDs in last 5000: {len(cpc_last)}")

except Exception as e:
    print(f"Error: {e}")
