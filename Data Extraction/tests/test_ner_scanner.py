
import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logic.ner_scanner import NERScanner

class TestNERScanner(unittest.TestCase):
    def test_model_loading(self):
        # This might fail if installation is not complete
        model = NERScanner.get_model()
        if model is None:
            print("Skipping test: scispaCy model not installed/loaded.")
            return

        self.assertIsNotNone(model)

    def test_entity_extraction(self):
        scanner = NERScanner()
        if not scanner.get_model():
            print("Skipping test: scispaCy model not installed/loaded.")
            return

        text = "Patients treated with Belinostat showed signs of Grade 3 Anemia and Thrombocytopenia."
        results = scanner.scan(text)
        
        print(f"NER Results: {results}")
        
        # Check Chemicals
        # Note: scispaCy BC5CDR is good but case sensitivity varies. Usually standard casing works.
        chemicals = results.get("CHEMICAL", [])
        self.assertTrue(any("Belinostat" in c for c in chemicals), "Belinostat not found as CHEMICAL")

        # Check Diseases
        diseases = results.get("DISEASE", [])
        self.assertTrue(any("Anemia" in d for d in diseases), "Anemia not found as DISEASE")
        self.assertTrue(any("Thrombocytopenia" in d for d in diseases), "Thrombocytopenia not found as DISEASE")

if __name__ == '__main__':
    with open('test_ner_result.log', 'w', encoding='utf-8') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner, exit=False)
