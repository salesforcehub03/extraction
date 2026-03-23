
import json
import os
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.logic.graph_builder import GraphBuilder
from src.logic.enrich_genomic_data import enrich_graph

EXTRACTED_DATA_PATH = "d:/AViiD/Data Extraction/belino_v13_extracted.json"
GRAPH_OUTPUT_PATH = "d:/AViiD/Data Extraction/belino_v13_extracted_graph.json"

def rebuild():
    print("1. Loading raw extracted data...")
    if not os.path.exists(EXTRACTED_DATA_PATH):
        print(f"Error: {EXTRACTED_DATA_PATH} not found.")
        return

    with open(EXTRACTED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("2. Building Graph with Strict Schema Enforced...")
    builder = GraphBuilder()
    graph = builder.build_graph(data)
    
    # Save graph
    with open(GRAPH_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
    print(f"   Graph saved to {GRAPH_OUTPUT_PATH}")
    print(f"   Nodes: {len(graph['nodes'])}")
    print(f"   Edges: {len(graph['edges'])}")

    print("3. Re-applying Genomic Enrichment...")
    enrich_graph()
    
    print("Done!")

if __name__ == "__main__":
    rebuild()
