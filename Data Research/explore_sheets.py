import pandas as pd

file_path = r"D:\AViiD\Data Research\belino-preclinial.xlsx"
output_file = r"D:\AViiD\Data Research\sheet_full_data.txt"

xl = pd.ExcelFile(file_path)

with open(output_file, 'w', encoding='utf-8') as f:
    for idx, name in enumerate(xl.sheet_names):
        try:
            df = pd.read_excel(file_path, sheet_name=name, header=None)
            f.write(f"=== SHEET {idx}: [{name.strip()}] === Shape: {df.shape}\n")
            for r in range(len(df)):
                vals = []
                for c in range(len(df.columns)):
                    v = df.iloc[r, c]
                    if pd.notna(v):
                        vals.append(f"C{c}:{v}")
                f.write(f"  Row {r}: {vals}\n")
            f.write("\n\n")
        except Exception as e:
            f.write(f"  ERROR: {e}\n\n")

print("Done!")
