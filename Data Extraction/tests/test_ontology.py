
import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logic.ontology import OntologyGrounder
from src.logic.graph_builder import GraphBuilder

class TestOntology(unittest.TestCase):
    def test_grounding_exact_match(self):
        term, conf = OntologyGrounder.ground_term("Anemia", "Adverse Event")
        self.assertEqual(term, "Anemia")
        self.assertEqual(conf, 1.0)
    
    def test_grounding_case_insensitivity(self):
        term, conf = OntologyGrounder.ground_term("anemia", "Adverse Event")
        self.assertEqual(term, "Anemia")
        self.assertEqual(conf, 1.0)

    def test_grounding_fuzzy_match(self):
        term, conf = OntologyGrounder.ground_term("Grade 3 Anemia", "Adverse Event")
        self.assertEqual(term, "Anemia")
        self.assertEqual(conf, 0.8)

    def test_grounding_target(self):
        term, conf = OntologyGrounder.ground_term("hdac", "Target")
        self.assertEqual(term, "HDAC")
        self.assertEqual(conf, 1.0)

    def test_graph_builder_integration(self):
        builder = GraphBuilder()
        mock_data = {
            "safety_data": {
                "adverse_events": [
                    {
                        "adverse_event_preferred_term": "severe anemia", # Should ground to Anemia
                        "grade_3_4_ae_frequency": "10%"
                    }
                ]
            },
             "mechanism_of_action": {
                "molecular_targets": ["hdac"] # Should ground to HDAC
            }
        }
        graph = builder.build_graph(mock_data)
        nodes = graph["nodes"]
        
        # Check AE Node
        ae_node = next((n for n in nodes if n["type"] == "Adverse Event"), None)
        self.assertIsNotNone(ae_node)
        self.assertEqual(ae_node["name"], "anemia") # Schema validator forces lowercase
        self.assertEqual(ae_node["properties"]["original_term"], "severe anemia")
        
        # Check Target Node
        target_node = next((n for n in nodes if n["type"] == "Target"), None)
        self.assertIsNotNone(target_node)
        self.assertEqual(target_node["name"], "hdac") # Schema validator forces lowercase

if __name__ == '__main__':
    with open('test_ontology_result.log', 'w', encoding='utf-8') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner, exit=False)
