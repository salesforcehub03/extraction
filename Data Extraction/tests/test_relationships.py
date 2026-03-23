
import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logic.graph_builder import GraphBuilder

class TestSemanticRelationships(unittest.TestCase):
    def setUp(self):
        self.builder = GraphBuilder()
        
    def test_semantic_relationship_processing(self):
        # Mock extracted data with semantic relationships
        mock_data = {
            "study_metadata": {
                "study_identifiers": ["ST-001"]
            },
            "semantic_relationships": {
                "relationships": [
                    {
                        "subject": "Belinostat", 
                        "predicate": "inhibits", 
                        "object": "HDAC Enzymes",
                        "confidence": "High"
                    },
                    {
                        "subject": "Grade 3 Anemia", 
                        "predicate": "caused by", 
                        "object": "Study Treatment"
                    }
                ]
            }
        }
        
        # Build Graph
        graph = self.builder.build_graph(mock_data)
        nodes = graph["nodes"]
        edges = graph["edges"]
        
        print(f"DEBUG: All Node Names: {[n['name'] for n in nodes]}")
        
        # 1. Verify Nodes exist (Belinostat, HDAC Enzymes)
        # Note: "Belinostat" might be created by _process_metadata or inferred. 
        # Here we rely on inference if not standard.
        belino_node = next((n for n in nodes if n["name"] == "Belinostat"), None)
        hdac_node = next((n for n in nodes if n["name"] == "HDAC Enzymes"), None)
        
        self.assertIsNotNone(belino_node, "Subject node not created")
        self.assertIsNotNone(hdac_node, "Object node not created")
        
        # 2. Verify Edge "inhibits"
        inhibit_edge = next((e for e in edges 
                             if e["source_id"] == belino_node["id"] 
                             and e["target_id"] == hdac_node["id"]
                             and e["type"] == "inhibits"), None)
        self.assertIsNotNone(inhibit_edge, "Semantic edge 'inhibits' not created")
        self.assertEqual(inhibit_edge["properties"]["confidence"], "High")

        # 3. Verify Edge "caused_by" (normalized from "caused by")
        anemia_node = next((n for n in nodes if n["name"] == "Grade 3 Anemia"), None)
        treatment_node = next((n for n in nodes if n["name"] == "Study Treatment"), None)
        
        caused_edge = next((e for e in edges 
                            if e["source_id"] == anemia_node["id"] 
                            and e["target_id"] == treatment_node["id"]
                            and e["type"] == "caused_by"), None)
        self.assertIsNotNone(caused_edge, "Semantic edge 'caused_by' not created")

if __name__ == '__main__':
    with open('test_relationships_result.log', 'w', encoding='utf-8') as f:
        # Redirect stdout to the file so we catch prints
        sys.stdout = f
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner, exit=False)
        sys.stdout = sys.__stdout__ # Reset stdout
