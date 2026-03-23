import pandas as pd

nodes = pd.read_csv(r"D:\AViiD\Data Research\preclinical_nodes.csv")
edges = pd.read_csv(r"D:\AViiD\Data Research\preclinical_edges.csv")

with open(r"D:\AViiD\Data Research\validation_report.txt", "w") as f:
    f.write(f"=== NODES: {len(nodes)} total ===\n")
    f.write(f"\n--- By Type ---\n")
    f.write(nodes["node_type"].value_counts().to_string() + "\n")

    f.write(f"\n=== EDGES: {len(edges)} total ===\n")
    f.write(f"\n--- By Type ---\n")
    f.write(edges["edge_type"].value_counts().to_string() + "\n")

    f.write(f"\n\n--- Node Columns ---\n")
    f.write(str(list(nodes.columns)) + "\n")
    
    f.write(f"\n--- Sample Nodes per Type ---\n")
    for t in nodes["node_type"].unique():
        subset = nodes[nodes["node_type"] == t].head(1)
        f.write(f"\n{t}:\n")
        for col in subset.columns:
            val = subset[col].values[0]
            if pd.notna(val) and str(val) != "":
                f.write(f"  {col}: {val}\n")
    
    f.write(f"\n--- Sample Edges per Type ---\n")
    for t in edges["edge_type"].unique():
        f.write(f"\n{t}:\n")
        sample = edges[edges["edge_type"] == t].head(2)
        f.write(sample.to_string() + "\n")

print("Validation done!")
