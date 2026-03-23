
import unittest
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logic.graph_builder import GraphBuilder

class TestGraphBuilder(unittest.TestCase):
    def setUp(self):
        print("DEBUG: Running updated test script")
        self.builder = GraphBuilder()
        
        # Mock Extracted Data
        self.mock_data = {
            "study_metadata": {
                "study_identifiers": ["CLN-19"],
                "study_phase": "Phase 2",
                "sponsor_information": "Spectrum"
            },
            "safety_data": {
                "adverse_events": [
                    {
                        "adverse_event_preferred_term": "Anemia",
                        "grade_3_4_ae_frequency": "10%",
                        "serious_adverse_event_flag": True
                    },
                    {
                        "adverse_event_preferred_term": "Thrombocytopenia"
                    }
                ]
            },
            "pharmacokinetics": {
                "alp_alkaline_phosphatase": "120 U/L",
                "alt_alanine_aminotransferase": "45 U/L"
            },
            "preclinical_toxicology": {
                "toxicity_species": ["Rat", "Dog"]
            },
            "mechanism_of_action": {
                "molecular_targets": ["HDAC"]
            }
        }

    def test_build_graph(self):
        graph = self.builder.build_graph(self.mock_data)
        
        # Verify Structure
        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)
        
        nodes = graph["nodes"]
        edges = graph["edges"]
        
        print(f"\nGenerated {len(nodes)} nodes and {len(edges)} edges.")
        
        # Verify Core Nodes
        study_node = next((n for n in nodes if n["type"] == "Clinical Study" and n["name"] == "cln-19"), None)
        self.assertIsNotNone(study_node, "Clinical Study node cln-19 not found")
        
        drug_node = next((n for n in nodes if n["type"] == "Drug" and n["name"] == "belinostat"), None)
        self.assertIsNotNone(drug_node, "Drug node Belinostat not found")
        
        # Verify Edges: Drug -> Tested In -> Study
        edge = next((e for e in edges if e["source_id"] == drug_node["id"] and e["target_id"] == study_node["id"] and e["type"] == "tested_in"), None)
        self.assertIsNotNone(edge, "Edge Drug -> Tested In -> Study not found")

        # Verify AE Nodes
        anemia_node = next((n for n in nodes if n["name"] == "anemia"), None)
        self.assertIsNotNone(anemia_node, "Anemia node not found")
        
        # Verify AE Edges: Anemia -> Observed In -> Study
        ae_edge = next((e for e in edges if e["source_id"] == anemia_node["id"] and e["target_id"] == study_node["id"] and e["type"] == "observed_in"), None)
        self.assertIsNotNone(ae_edge, "Edge Anemia -> Observed In -> Study not found")
        
        # Verify Biomarkers
        alt_node = next((n for n in nodes if n["name"] == "alt_alanine_aminotransferase" or n["name"] == "alt"), None) # Name logic check
         # In graph builder I used "ALT" as name for "alt_alanine_aminotransferase" key text
        self.assertIsNotNone(alt_node, "ALT node not found")

        # Verify Preclinical
        rat_study = next((n for n in nodes if n["type"] == "Animal Study" and "rat" in n["name"]), None)
        self.assertIsNotNone(rat_study, "Rat Study node not found")
        
        # Verify Target
        target_node = next((n for n in nodes if n["type"] == "Target" and n["name"] == "hdac"), None)
        self.assertIsNotNone(target_node, "HDAC Target node not found")

if __name__ == '__main__':
    with open('test_result.log', 'w', encoding='utf-8') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner, exit=False)
