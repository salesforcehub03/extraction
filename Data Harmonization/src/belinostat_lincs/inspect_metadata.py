
import pandas as pd
import gzip

def inspect():
    inst_info_file = r"D:\AViiD\GSE92742_Broad_LINCS_inst_info.txt.gz"
    
    print(f"Loading {inst_info_file}...")
    df = pd.read_csv(inst_info_file, sep='\t', compression='gzip', low_memory=False)
    
    print(f"Total Rows: {len(df)}")
    print("\nFirst 5 entries:")
    print(df.head(5).to_string())
    
    # Check for 'REP' in inst_id
    print("\nChecking for 'REP' in 'inst_id' (first 5 matches)...")
    rep_matches = df[df['inst_id'].astype(str).str.contains('REP')]
    if not rep_matches.empty:
        print(rep_matches.head(5).to_string())
    else:
        print("No 'REP' found in inst_id.")
        
    # Check for 'REP' in rna_plate
    print("\nChecking for 'REP' in 'rna_plate' (first 5 matches)...")
    rep_plate_matches = df[df['rna_plate'].astype(str).str.contains('REP')]
    if not rep_plate_matches.empty:
        print(rep_plate_matches.head(5).to_string())
    else:
        print("No 'REP' found in rna_plate.")
        
    # Check for 'LJP' in rna_plate
    print("\nChecking for 'LJP' in 'rna_plate' (first 5 matches)...")
    ljp_matches = df[df['rna_plate'].astype(str).str.contains('LJP')]
    if not ljp_matches.empty:
        print(ljp_matches.head(5).to_string())
    else:
        print("No 'LJP' found in rna_plate.")

if __name__ == "__main__":
    inspect()
