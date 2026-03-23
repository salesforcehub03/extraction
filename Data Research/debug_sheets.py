import pandas as pd

xl = pd.ExcelFile(r"D:\AViiD\Data Research\belino-preclinial.xlsx")
with open(r"D:\AViiD\Data Research\sheet_names_repr.txt", "w") as f:
    for i, s in enumerate(xl.sheet_names):
        f.write(f"{i}: {repr(s)}\n")
print("Done")
