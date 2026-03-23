
import json
import os

GRAPH_FILE_PATH = "d:/AViiD/Data Extraction/belino_v13_extracted_graph.json"
OUTPUT_HTML_PATH = "d:/AViiD/Data Extraction/graph_visualizer.html"

def generate_visualization():
    if not os.path.exists(GRAPH_FILE_PATH):
        print(f"Error: {GRAPH_FILE_PATH} not found.")
        return

    with open(GRAPH_FILE_PATH, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    # Prepare Cytoscape Elements
    elements = []
    
    # Collect all unique node types for the filter menu
    node_types = set()

    # Nodes
    for node in graph_data.get("nodes", []):
        n_type = node.get("type", "Unknown")
        node_types.add(n_type)
        
        # Format properties for display
        props_html = "<table class='prop-table'>"
        for k, v in node.get("properties", {}).items():
            props_html += f"<tr><td>{k}</td><td>{v}</td></tr>"
        props_html += "</table>"

        elements.append({
            "data": {
                "id": node["id"],
                "label": node["name"],
                "type": n_type,
                "color": get_node_color(n_type),
                "properties": props_html,
                "raw_properties": node.get("properties", {})
            }
        })
    
    # Edges
    for edge in graph_data.get("edges", []):
        elements.append({
            "data": {
                "source": edge["source_id"],
                "target": edge["target_id"],
                "label": edge["type"],
                "confidence": edge.get("confidence", 1.0)
            }
        })

    # Generate Type Filters HTML
    filters_html = ""
    for nt in sorted(node_types):
        color = get_node_color(nt)
        filters_html += f"""
        <label class="filter-item">
            <input type="checkbox" checked onchange="toggleType(this, '{nt}')">
            <span class="legend-color" style="background-color: {color};"></span>
            {nt}
        </label>
        """

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Belino-IB Interactive Knowledge Graph</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
    <style>
        :root {{
            --bg-color: #1e1e1e;
            --panel-bg: #252526;
            --border-color: #333;
            --text-color: #d4d4d4;
            --accent-color: #007acc;
        }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0; 
            padding: 0; 
            background-color: var(--bg-color); 
            color: var(--text-color);
            height: 100vh;
            display: flex;
            overflow: hidden;
        }}
        #sidebar {{
            width: 300px;
            background-color: var(--panel-bg);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            box-shadow: 2px 0 5px rgba(0,0,0,0.3);
            z-index: 10;
        }}
        #sidebar-header {{
            padding: 15px;
            border-bottom: 1px solid var(--border-color);
        }}
        h1 {{ margin: 0; font-size: 1.1em; color: #4fc1ff; }}
        h2 {{ margin: 0 0 10px 0; font-size: 1em; color: #fff; }}
        
        #controls {{
            padding: 15px;
            border-bottom: 1px solid var(--border-color);
            overflow-y: auto;
            flex-shrink: 0;
            max-height: 40%;
        }}
        .search-box {{
            width: 100%;
            padding: 8px;
            margin-bottom: 15px;
            background-color: #3c3c3c;
            border: 1px solid #333;
            color: #fff;
            border-radius: 4px;
        }}
        .search-box:focus {{ outline: 1px solid var(--accent-color); }}
        
        .filter-group {{ display: flex; flex-direction: column; gap: 5px; }}
        .filter-item {{ display: flex; align-items: center; font-size: 0.9em; cursor: pointer; }}
        .filter-item input {{ margin-right: 8px; }}
        .legend-color {{ width: 12px; height: 12px; display: inline-block; margin-right: 8px; border-radius: 3px; }}

        #details-panel {{
            padding: 15px;
            overflow-y: auto;
            flex-grow: 1;
        }}
        .prop-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85em;
        }}
        .prop-table td {{
            padding: 6px;
            border-bottom: 1px solid #3c3c3c;
            vertical-align: top;
        }}
        .prop-table td:first-child {{
            font-weight: bold;
            color: #9cdcfe;
            width: 35%;
        }}
        
        #main {{
            flex-grow: 1;
            position: relative;
        }}
        #cy {{
            width: 100%;
            height: 100%;
            display: block;
        }}
        
        /* Tooltip-like overlay for quick info */
        #node-tooltip {{
            position: absolute;
            display: none;
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid #555;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 0.8em;
            pointer-events: none;
            z-index: 100;
        }}
    </style>
</head>
<body>
    <div id="sidebar">
        <div id="sidebar-header">
            <h1>Graph Explorer</h1>
        </div>
        <div id="controls">
            <input type="text" id="search" class="search-box" placeholder="Search nodes..." onkeyup="searchNodes()">
            <h2>Filters</h2>
            <div class="filter-group">
                {filters_html}
            </div>
        </div>
        <div id="details-panel">
            <h2>Node Details</h2>
            <p style="color: #888; font-style: italic;">Click a node to view properties.</p>
        </div>
    </div>
    
    <div id="main">
        <div id="cy"></div>
        <div id="node-tooltip"></div>
    </div>

    <script>
        var elements = {json.dumps(elements)};
        
        var cy = cytoscape({{
            container: document.getElementById('cy'),
            elements: elements,
            style: [
                {{
                    selector: 'node',
                    style: {{
                        'label': 'data(label)',
                        'background-color': 'data(color)',
                        'color': '#fff',
                        'font-size': '10px',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'width': 'label',
                        'height': 'label',
                        'padding': '8px',
                        'text-outline-width': 1,
                        'text-outline-color': '#111',
                        'border-width': 0,
                        'transition-property': 'background-color, line-color, target-arrow-color',
                        'transition-duration': '0.5s'
                    }}
                }},
                {{
                    selector: 'node:selected',
                    style: {{
                        'border-width': 2,
                        'border-color': '#fff',
                        'text-outline-color': '#000',
                        'text-outline-width': 2,
                        'font-size': '12px',
                        'font-weight': 'bold',
                        'z-index': 9999
                    }}
                }},
                {{
                    selector: 'edge',
                    style: {{
                        'width': 1,
                        'line-color': '#444',
                        'target-arrow-color': '#444',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'opacity': 0.6,
                        'arrow-scale': 0.8
                    }}
                }},
                {{
                    selector: 'edge:selected',
                    style: {{
                        'width': 2,
                        'line-color': '#007acc',
                        'target-arrow-color': '#007acc',
                        'opacity': 1,
                        'label': 'data(label)',
                        'font-size': '8px',
                        'color': '#fff',
                        'text-background-opacity': 1,
                        'text-background-color': '#1e1e1e',
                        'text-background-padding': '2px'
                    }}
                }},
                {{
                    selector: 'node[type="Drug"]',
                    style: {{ 'width': 35, 'height': 35, 'font-size': '14px', 'font-weight': 'bold' }}
                }},
                {{
                    selector: 'node[type="Clinical Study"]',
                    style: {{ 'shape': 'rectangle' }}
                }},
                 {{
                    selector: '.faded',
                    style: {{
                        'opacity': 0.1,
                        'text-opacity': 0
                    }}
                }}
            ],
            layout: {{
                name: 'cose',
                animate: false,
                randomize: false,
                componentSpacing: 100,
                nodeRepulsion: 800000,
                nodeOverlap: 20,
                idealEdgeLength: 100,
                edgeElasticity: 100,
                nestingFactor: 5,
                gravity: 80,
                numIter: 1000,
                initialTemp: 200,
                coolingFactor: 0.95,
                minTemp: 1.0
            }}
        }});

        // Function to toggle node types
        function toggleType(checkbox, type) {{
            var display = checkbox.checked ? 'element' : 'none';
            cy.nodes('[type="' + type + '"]').style('display', display);
        }}

        // Search Function
        function searchNodes() {{
            var query = document.getElementById('search').value.toLowerCase();
            if(!query) {{
                cy.elements().removeClass('faded');
                return;
            }}
            
            var matched = cy.nodes().filter(function(ele){{
                return ele.data('label').toLowerCase().includes(query) || 
                       ele.data('type').toLowerCase().includes(query);
            }});
            
            cy.elements().addClass('faded');
            matched.removeClass('faded');
            matched.neighborhood().removeClass('faded');
        }}

        // Click Event: Populate Side Panel
        cy.on('tap', 'node', function(evt){{
            var node = evt.target;
            var detailsHtml = "<h2>" + node.data('label') + "</h2>";
            detailsHtml += "<p style='color: " + node.data('color') + "'>" + node.data('type') + "</p>";
            
            if (node.data('properties')) {{
                detailsHtml += "<h3>Properties</h3>" + node.data('properties');
            }}
            
            document.getElementById('details-panel').innerHTML = detailsHtml;
        }});

        // Reset sidebar on background tap
        cy.on('tap', function(evt){{
            if(evt.target === cy){{
                document.getElementById('details-panel').innerHTML = "<h2>Node Details</h2><p style='color: #888; font-style: italic;'>Click a node to view properties.</p>";
                cy.elements().removeClass('faded'); // Clear search highlight on bg click? Optional.
            }}
        }});

    </script>
</body>
</html>
    """
    
    with open(OUTPUT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Interactive Visualization generated at: {OUTPUT_HTML_PATH}")

def get_node_color(node_type):
    colors = {
        "Drug": "#4CAF50",         # Green
        "Adverse Event": "#F44336", # Red
        "Clinical Study": "#2196F3",# Blue
        "Biomarker": "#9C27B0",    # Purple
        "Target": "#FF9800",       # Orange
        "Animal Study": "#795548", # Brown
        "Pathway": "#E91E63",      # Pink
    }
    return colors.get(node_type, "#607D8B") # Grey default

if __name__ == "__main__":
    generate_visualization()
