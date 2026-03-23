import spacy
from typing import List, Dict, Any

class NERScanner:
    """
    Wraps scispaCy models to extract medical entities (Chemicals, Diseases).
    Acts as a validation layer for the LLM.
    """
    
    _model = None
    _tried_load = False
    
    @classmethod
    def get_model(cls):
        if cls._model is None and not cls._tried_load:
            try:
                cls._tried_load = True
                # Prefer BC5CDR (BioCreative V Chemical Disease Relation) model
                # It is specifically trained for Chemicals and Diseases
                print("Loading scispaCy model 'en_ner_bc5cdr_md'...")
                cls._model = spacy.load("en_ner_bc5cdr_md")
            except Exception as e:
                print(f"Warning: NERScanner model 'en_ner_bc5cdr_md' not found. ScispaCy NER will be skipped. Use 'pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz' to install.")
                return None
        return cls._model

    def scan(self, text: str) -> Dict[str, List[str]]:
        """
        Scans text and returns a dict of extracted entities by type.
        Returns:
            {
                "CHEMICAL": ["Belinostat", "Warfarin"],
                "DISEASE": ["Lymphoma", "Anemia"]
            }
        """
        nlp = self.get_model()
        if not nlp or not text:
            return {}
            
        doc = nlp(text)
        
        results = {
            "CHEMICAL": [],
            "DISEASE": []
        }
        
        for ent in doc.ents:
            # scispaCy BC5CDR model uses 'CHEMICAL' and 'DISEASE' labels
            label = ent.label_
            text = ent.text.strip()
            
            if label in results:
                if text not in results[label]: # Dedup
                    results[label].append(text)
            else:
                # Catch other potential labels if we switch models
                results.setdefault(label, []).append(text)
                
        return results
