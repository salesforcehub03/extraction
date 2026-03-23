
import json
import csv
import os

GRAPH_FILE_PATH = "d:/AViiD/Data Extraction/belino_v13_extracted_graph.json"
NODES_CSV_PATH = "d:/AViiD/Data Extraction/graph_nodes.csv"
EDGES_CSV_PATH = "d:/AViiD/Data Extraction/graph_edges.csv"

def export_to_csv():
    if not os.path.exists(GRAPH_FILE_PATH):
        print(f"Error: {GRAPH_FILE_PATH} not found.")
        return

    with open(GRAPH_FILE_PATH, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    # Export Nodes
    # We need to flatten properties for CSV
    all_property_keys = set()
    node_rows = []
    
    for node in graph_data.get("nodes", []):
        props = node.get("properties", {})
        all_property_keys.update(props.keys())
        
        row = {
            "id": node["id"],
            "Label": node["name"],
            "Type": node.get("type", "Unknown")
        }
        # Flatten properties
        for k, v in props.items():
            row[k] = str(v) # Ensure string format for CSV
            
        node_rows.append(row)
    
    # Sort keys for consistent columns
    sorted_prop_keys = sorted(list(all_property_keys))
    node_headers = ["id", "Label", "Type"] + sorted_prop_keys
    
    print(f"   -> Found {len(all_property_keys)} unique properties across {len(node_rows)} nodes.")
    
    with open(NODES_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=node_headers, extrasaction='ignore') # Ignore extra keys if any
        writer.writeheader()
        writer.writerows(node_rows)
            
    print(f"Nodes exported to: {NODES_CSV_PATH}")

    # Export Edges
    edge_headers = ["Source", "Target", "Type", "Confidence", "Source_Tool"]
    
    with open(EDGES_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=edge_headers)
        writer.writeheader()
        
        for edge in graph_data.get("edges", []):
            props = edge.get("properties", {})
            row = {
                "Source": edge["source_id"],
                "Target": edge["target_id"],
                "Type": edge["type"],
                "Confidence": edge.get("confidence", 1.0),
                "Source_Tool": props.get("source", "LLM")
            }
            writer.writerow(row)
            
    print(f"Edges exported to: {EDGES_CSV_PATH}")

if __name__ == "__main__":
    export_to_csv()
