import pandas as pd
from pathlib import Path
from typing import List

def merge_files(base_excel_path: Path, other_files: List[Path], output_path: Path) -> Path:
    """
    Merges a base Excel file with other Excel/CSV files into a single consolidated workbook.
    
    Args:
        base_excel_path: Path to the main IB Excel file (extraction output).
        other_files: List of paths to other files (Clinical, Preclinical, etc.).
        output_path: Path to save the consolidated Excel file.
        
    Returns:
        Path to the saved consolidated file.
    """
    print(f"Merging files into {output_path}...")
    
    # 1. Load the Base Excel (IB Data)
    # We use a dict to store all sheets {sheet_name: dataframe}
    all_sheets = {}
    
    if base_excel_path.exists():
        print(f"Loading base file: {base_excel_path.name}")
        xl = pd.ExcelFile(base_excel_path)
        for sheet_name in xl.sheet_names:
            all_sheets[sheet_name] = xl.parse(sheet_name)
    else:
        print(f"Warning: Base file {base_excel_path} not found.")

    # 2. Process Other Files
    for file_path in other_files:
        if not file_path.exists():
            continue
            
        print(f"Processing additional file: {file_path.name}")
        
        # Determine clean name for sheets
        base_name = file_path.stem.replace(" ", "_")[:25] # Excel sheet limit 31 chars
        
        if file_path.suffix.lower() == '.csv':
            try:
                df = pd.read_csv(file_path)
                sheet_name = base_name
                # Avoid duplicate sheet names
                counter = 1
                while sheet_name in all_sheets:
                    sheet_name = f"{base_name}_{counter}"
                    counter += 1
                all_sheets[sheet_name] = df
            except Exception as e:
                print(f"Error reading CSV {file_path}: {e}")
                
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            try:
                xl = pd.ExcelFile(file_path)
                for sn in xl.sheet_names:
                    df = xl.parse(sn)
                    # Prefix sheet name with file name to avoid collisions and provide context
                    # e.g. "Clinical_Demographics"
                    new_sheet_name = f"{base_name}_{sn}".replace(" ", "_")[:31]
                    
                    # Ensure uniqueness
                    counter = 1
                    while new_sheet_name in all_sheets:
                        new_sheet_name = f"{new_sheet_name[:28]}_{counter}"
                        counter += 1
                        
                    all_sheets[new_sheet_name] = df
            except Exception as e:
                print(f"Error reading Excel {file_path}: {e}")

    # 3. Write Consolidated File
    print(f"Writing {len(all_sheets)} sheets to {output_path}...")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet_name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
    return output_path
