
import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logic.graph_builder import GraphBuilder
from src.logic.entity_resolver import EntityResolver

class TestEntityResolution(unittest.TestCase):
    def setUp(self):
        self.resolver = EntityResolver(threshold=0.85)
        self.builder = GraphBuilder()

    def test_basic_resolver(self):
        # simple list matching
        existing = ["Anemia", "Thrombocytopenia"]
        
        # Exact match
        match, score = self.resolver.resolve("Anemia", existing)
        self.assertEqual(match, "Anemia")
        self.assertEqual(score, 1.0)
        
        # Fuzzy match
        match, score = self.resolver.resolve("Anaemia", existing) # "Anaemia" vs "Anemia"
        self.assertEqual(match, "Anemia")
        self.assertGreater(score, 0.85)
        
        # No match
        match, score = self.resolver.resolve("Headache", existing)
        self.assertIsNone(match)

    def test_graph_builder_merging(self):
        # Test that graph builder merges similar nodes
        mock_data = {
            "semantic_relationships": {
                "relationships": [
                    # First mention: "Grade 3 Anemia"
                    {"subject": "Belinostat", "predicate": "causes", "object": "Grade 3 Anemia"},
                    # Second mention: "Anemia (Grade 3)" -> Should merge with above? 
                    # Actually fuzzy match might not catch "Grade 3 Anemia" vs "Anemia (Grade 3)" depending on algo
                    # Let's try simpler typo: "Severe Anemia" vs "Severe Anaemia"
                    {"subject": "PXD101", "predicate": "causes", "object": "Severe Anemia"},
                    {"subject": "Belinostat", "predicate": "causes", "object": "Severe Anaemia"}
                ]
            }
        }
        
        graph = self.builder.build_graph(mock_data)
        nodes = graph["nodes"]
        
        # Print nodes for debugging
        print(f"DEBUG: Nodes: {[n['name'] for n in nodes]}")
        
        # Check if "Severe Anemia" and "Severe Anaemia" became one node
        anemia_nodes = [n for n in nodes if "Anemia" in n["name"] or "Anaemia" in n["name"]]
        
        # We expect exactly 1 node for "Severe Anemia/Anaemia" if they merged
        # However, "Grade 3 Anemia" is distinct.
        
        severe_nodes = [n for n in anemia_nodes if "Severe" in n["name"]]
        self.assertEqual(len(severe_nodes), 1, f"Expected 1 merged node for Severe Anemia, found: {[n['name'] for n in severe_nodes]}")

if __name__ == '__main__':
      with open('test_resolution_result.log', 'w', encoding='utf-8') as f:
        # Redirect stdout to the file so we catch prints
        sys.stdout = f
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner, exit=False)
        sys.stdout = sys.__stdout__ # Reset stdout
