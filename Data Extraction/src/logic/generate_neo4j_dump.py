
import json
import os

GRAPH_FILE_PATH = "d:/AViiD/Data Extraction/belino_v13_extracted_graph.json"
CYPHER_OUTPUT_PATH = "d:/AViiD/Data Extraction/belino_graph_dump.cypher"

def escape_string(s):
    if isinstance(s, str):
        # Escape single quotes and backslashes
        return s.replace('\\', '\\\\').replace("'", "\\'")
    return s

def format_value(v):
    if isinstance(v, (int, float, bool)):
        return str(v).lower() if isinstance(v, bool) else str(v)
    if v is None:
        return "null"
    return f"'{escape_string(str(v))}'"

def generate_cypher():
    if not os.path.exists(GRAPH_FILE_PATH):
        print(f"Error: {GRAPH_FILE_PATH} not found.")
        return

    with open(GRAPH_FILE_PATH, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    cypher_lines = []
    cypher_lines.append("// Cypher Dump for Belino-IB Knowledge Graph")
    cypher_lines.append("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE;")
    cypher_lines.append("")

    # Nodes
    # We use MERGE to be safe, or just CREATE since we know IDs are unique in our JSON.
    # To handle labels dynamically: (n:Label)
    # But names often have spaces or special chars, so we use :`Label`
    
    print("Generating Node statements...")
    for node in graph_data.get("nodes", []):
        node_id = node["id"]
        # Sanitize label (Type)
        node_type = node.get("type", "Entity").replace(" ", "_")
        
        props_str_list = []
        props_str_list.append(f"id: {format_value(node_id)}")
        props_str_list.append(f"name: {format_value(node['name'])}")
        
        for k, v in node.get("properties", {}).items():
            # Sanitize property key
            clean_k = k.replace(" ", "_").replace("-", "_")
            props_str_list.append(f"`{clean_k}`: {format_value(v)}")
            
        props_body = ", ".join(props_str_list)
        
        # Using MERGE to ensure idempotency if run multiple times
        # Note: In a pure dump, CREATE is faster, but MERGE is safer for users rerunning chunks.
        # We will use CREATE for speed as the graph is clean.
        line = f"CREATE (:`{node_type}` {{{props_body}}});"
        cypher_lines.append(line)

    cypher_lines.append("")
    cypher_lines.append("// Indexing for Edge creation performance")
    cypher_lines.append("CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.id);")
    cypher_lines.append("")

    # Edges
    print("Generating Edge statements...")
    # Group edges to process in batches if needed, but simple MATCH-CREATE is fine for this size.
    # MATCH (a), (b) WHERE a.id = '...' AND b.id = '...' CREATE (a)-[:TYPE]->(b)
    
    for edge in graph_data.get("edges", []):
        source_id = edge["source_id"]
        target_id = edge["target_id"]
        edge_type = edge["type"].replace(" ", "_").replace("-", "_").upper()
        
        props_str_list = []
        # Add explicit confidence if present
        if "confidence" in edge:
            props_str_list.append(f"confidence: {edge['confidence']}")
            
        for k, v in edge.get("properties", {}).items():
             clean_k = k.replace(" ", "_").replace("-", "_")
             props_str_list.append(f"`{clean_k}`: {format_value(v)}")

        props_body = ""
        if props_str_list:
            props_body = f" {{{', '.join(props_str_list)}}}"
            
        # Optimization: We can't easily use "MATCH (a:Type)" because we don't strictly track SourceNode Type in edge list
        # So we match globally on ID. This relies on the global index or constraint we added at the top.
        # However, Cypher requires knowing labels for efficient MATCH? Not strictly, but it helps.
        # We'll just MATCH (a {id: ...}), (b {id: ...}) 
        
        line = f"MATCH (a {{id: {format_value(source_id)}}}), (b {{id: {format_value(target_id)}}}) CREATE (a)-[:`{edge_type}`{props_body}]->(b);"
        cypher_lines.append(line)

    with open(CYPHER_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(cypher_lines))
        
    print(f"Cypher dump generated at: {CYPHER_OUTPUT_PATH}")
    print(f"Total statements: {len(cypher_lines)}")

if __name__ == "__main__":
    generate_cypher()
