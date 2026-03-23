
import pandas as pd
import gzip

def inspect():
    sig_info_file = r"D:\AViiD\GSE92742_Broad_LINCS_sig_info.txt.gz"
    
    print(f"Loading {sig_info_file}...")
    df = pd.read_csv(sig_info_file, sep='\t', compression='gzip', low_memory=False)
    
    print(f"Total Rows: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")
    
    # Check if row count matches GCTX columns (118050)
    print(f"Matches GCTX column count (118050)? {len(df) == 118050}")
    
    # Filter for Belinostat
    print("Filtering for Belinostat...")
    bel_df = df[df['pert_iname'].str.lower().isin(['belinostat', 'pxd101'])]
    
    if bel_df.empty:
        print("No Belinostat entries found!")
        return
        
    print(f"Found {len(bel_df)} entries.")
    
    # Show first 5 entries
    print("\nFirst 5 Belinostat entries:")
    print(bel_df.head(5).to_string())
    
    # Check for 'REP' in IDs
    print("\nChecking for 'REP' string in 'sig_id' or 'distil_id'...")
    if 'sig_id' in df.columns:
        print(f"Sample sig_id: {df['sig_id'].iloc[0]}")
    if 'distil_id' in df.columns:
        print(f"Sample distil_id: {df['distil_id'].iloc[0]}")

if __name__ == "__main__":
    inspect()
