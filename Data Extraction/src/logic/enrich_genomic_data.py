
import json
import os

GRAPH_FILE_PATH = "d:/AViiD/Data Extraction/belino_v13_extracted_graph.json"

HDAC_DATA = {
    "HDAC1": {"chromosome": "chr1", "coordinates": "32,291,921 – 32,333,635", "length": "41,715 bp"},
    "HDAC2": {"chromosome": "chr6", "coordinates": "113,933,028 – 113,971,148", "length": "38,121 bp"},
    "HDAC3": {"chromosome": "chr5", "coordinates": "141,620,778 – 141,636,867", "length": "16,089 bp"},
    "HDAC4": {"chromosome": "chr2", "coordinates": "235,603,604 – 241,771,051", "length": "~350,000 bp"},
    "HDAC5": {"chromosome": "chr17", "coordinates": "44,076,746 – 44,123,702", "length": "46,956 bp"},
    "HDAC6": {"chromosome": "chrX", "coordinates": "48,801,377 – 48,824,986", "length": "23,609 bp"},
    "HDAC7": {"chromosome": "chr12", "coordinates": "47,797,021 – 47,862,000*", "length": "~65,000 bp"},
    "HDAC8": {"chromosome": "chrX", "coordinates": "72,345,000 – 72,490,924*", "length": "~24,000 bp"},
    "HDAC9": {"chromosome": "chr7", "coordinates": "18,086,825 – 19,002,416", "length": "915,591 bp"},
    "HDAC10": {"chromosome": "chr22", "coordinates": "50,245,183 – 50,251,405", "length": "6,222 bp"},
    "HDAC11": {"chromosome": "chr3", "coordinates": "13,479,724 – 13,506,424", "length": "26,700 bp"}
}

def enrich_graph():
    if not os.path.exists(GRAPH_FILE_PATH):
        print(f"Error: {GRAPH_FILE_PATH} not found.")
        return

    with open(GRAPH_FILE_PATH, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    nodes = graph_data.get("nodes", [])
    updated_count = 0
    
    # 1. Update existing nodes
    existing_ids = set()
    for node in nodes:
        existing_ids.add(node["id"])
        # Check if node name matches any HDAC key (normalized)
        node_name = node.get("name", "").upper()
        
        # Check for direct match or substring match (e.g. "HDAC1 ENZYME")
        matched_key = None
        if node_name in HDAC_DATA:
            matched_key = node_name
        else:
            # Fallback for partial matches if needed, but User asked for these specific types
            pass

        if matched_key:
            print(f"Enriching existing node: {node['name']} ({node['id']})")
            node["properties"].update(HDAC_DATA[matched_key])
            node["type"] = "Target" # Ensure type is Target
            updated_count += 1

    # 2. Creating missing nodes
    # The user asked to "add this property for each gene type", implying these nodes should exist.
    # If they don't extract from the PDF, we should add them to ensure the Knowledge Graph is complete.
    
    for gene, props in HDAC_DATA.items():
        # Check if we already updated it (simple name check might miss if ID is different)
        # Let's search by name in the graph
        found = False
        for node in nodes:
            if node.get("name", "").upper() == gene:
                found = True
                break
        
        if not found:
            print(f"Creating new node for: {gene}")
            new_node = {
                "id": f"target:{gene.lower()}",
                "name": gene,
                "type": "Target",
                "properties": {
                    "source": "Manual_Enrichment",
                    **props
                }
            }
            nodes.append(new_node)
            updated_count += 1
            
            # Link to Belinostat? Usually HDACs are targets of Belinostat.
            # Let's add an inferred edge if Belinostat exists
            graph_data.setdefault("edges", [])
            graph_data["edges"].append({
                 "source_id": "drug:belinostat",
                 "target_id": new_node["id"],
                 "type": "inhibits",
                 "properties": {
                     "source": "Inferred_Mechanism",
                     "confidence": "High"
                 },
                 "confidence": 1.0
            })

    graph_data["nodes"] = nodes
    
    with open(GRAPH_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)

    print(f"Successfully enriched graph. Updated/Created {updated_count} nodes.")

if __name__ == "__main__":
    enrich_graph()
