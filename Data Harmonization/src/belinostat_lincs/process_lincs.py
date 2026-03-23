
import os
import gzip
import pandas as pd
from cmapPy.pandasGEXpress.parse import parse

def main():
    # Define file paths
    gctx_file = r"D:\AViiD\GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328_2017-03-06.gctx\GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328.gctx"
    inst_info_file = r"D:\AViiD\GSE92742_Broad_LINCS_inst_info.txt.gz"
    output_file = "belinostat_only.csv"
    
    print(f"Processing file: {gctx_file}")
    
    if not os.path.exists(gctx_file):
        print(f"Error: GCTX file not found at {gctx_file}")
        return

    if not os.path.exists(inst_info_file):
        print(f"Error: Metadata file not found at {inst_info_file}")
        return

    try:
        # 1. Load external metadata
        print(f"Loading metadata from {inst_info_file}...")
        # inst_info is usually tab-separated
        inst_info = pd.read_csv(inst_info_file, sep='\t', compression='gzip', low_memory=False)
        
        print(f"Loaded metadata shape: {inst_info.shape}")
        print(f"Columns: {inst_info.columns.tolist()}")
        
        # 2. Filter for 'belinostat' and 'pxd101'
        print("Filtering for Belinostat/PXD101...")
        
        # Check column names - usually 'pert_iname', but sometimes 'pert_name' or similar
        pert_col = 'pert_iname'
        if pert_col not in inst_info.columns:
             # Try to find a similar column
             candidates = [c for c in inst_info.columns if 'pert' in c and 'name' in c]
             if candidates:
                 pert_col = candidates[0]
                 print(f"Using column '{pert_col}' for perturbation name.")
             else:
                 print("Error: Could not find perturbation name column.")
                 return

        # Case-insensitive filter
        matched_meta = inst_info[
            inst_info[pert_col].astype(str).str.lower().isin(['belinostat', 'pxd101'])
        ]
        
        print(f"Found {len(matched_meta)} matching samples in metadata.")
        
        if matched_meta.empty:
            print("No matching samples found in metadata.")
            return

        # 3. Get the sample IDs matching the GCTX file
        # The GCTX columns are usually 'distil_id' or 'id' in metadata
        # Let's inspect GCTX columns first to see what they look like
        print("Reading GCTX column headers to match IDs...")
        col_meta_gctx = parse(gctx_file, col_meta_only=True)
        if hasattr(col_meta_gctx, 'col_metadata_df'):
            gctx_ids = col_meta_gctx.col_metadata_df.index.tolist()
        else:
            gctx_ids = col_meta_gctx.index.tolist()
            
        print(f"GCTX has {len(gctx_ids)} columns.")
        print(f"Sample GCTX ID: {gctx_ids[0]}")
        
        # Determine which metadata column matches GCTX IDs
        # The GCTX ID format 'REP.A001_A375_24H:A03' matches 'rna_plate:rna_well'
        # 3. Get the sample IDs matching the GCTX file
        print("Reading GCTX column headers to match IDs...")
        col_meta_gctx = parse(gctx_file, col_meta_only=True)
        if hasattr(col_meta_gctx, 'col_metadata_df'):
            gctx_ids = col_meta_gctx.col_metadata_df.index.tolist()
        else:
            gctx_ids = col_meta_gctx.index.tolist()
            
        print(f"GCTX has {len(gctx_ids)} columns.")
        print(f"Sample GCTX ID: {gctx_ids[0]}")
        
        # Check for intersection
        # Try exact match with inst_id
        target_ids = set(matched_meta['inst_id']).intersection(set(gctx_ids))
        
        if not target_ids:
            print("\nWARNING: No exact matches found between metadata 'inst_id' and GCTX columns.")
            # Debugging info
            print(f"Metadata ID examples (Belinostat): {matched_meta['inst_id'].head().tolist()}")
            print(f"GCTX ID examples: {gctx_ids[:5]}")
            
            # Check for plate prefixes
            meta_plates = matched_meta['rna_plate'].unique()
            print(f"\nMetadata Plates for Belinostat: {meta_plates}")
            
            gctx_prefixes = set([x.split('_')[0] for x in gctx_ids[:100]])
            print(f"GCTX Plate Prefixes (first 100): {gctx_prefixes}")
            
            common_prefixes = set([x.split('_')[0] for x in gctx_ids]).intersection(set([x.split('_')[0] for x in matched_meta['inst_id']]))
            print(f"Common Plate Prefixes in entire file: {common_prefixes}")
            
            print("\nCONCLUSION: The GCTX file does not contain the specific plates/samples for Belinostat.")
            print("The GCTX file appears to contain 'REP' and 'LJP' plates, while Belinostat is on 'CPC' and 'MUC' plates.")
            return

        print(f"Found {len(target_ids)} matching samples present in GCTX file.")
        
        # 4. Parse data for filtered columns
        print("Extracting data for target columns...")
        bel_data = parse(gctx_file, cid=list(target_ids))
        
        # 5. Extract DataFrame
        bel_df = bel_data.data_df
        
        # 6. Save to CSV
        print(f"Saving to {output_file}...")
        bel_df.to_csv(output_file)
        print("Done!")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
