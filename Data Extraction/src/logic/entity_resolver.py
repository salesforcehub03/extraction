
import difflib
from typing import List, Optional, Tuple

class EntityResolver:
    """
    Handles fuzzy matching and deduplication of entities.
    Uses SequenceMatcher to find similar strings.
    """
    
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold

    def resolve(self, name: str, existing_names: List[str]) -> Tuple[Optional[str], float]:
        """
        Check if 'name' is similar enough to any string in 'existing_names'.
        Returns (Match Name, Score) or (None, 0.0) if no match found.
        """
        if not name or not existing_names:
            return None, 0.0
            
        # Normalize input for comparison (lowercase, stripped)
        query = name.lower().strip()
        
        best_match = None
        best_score = 0.0
        
        for existing in existing_names:
            target = existing.lower().strip()
            
            # Exact match optimization
            if query == target:
                return existing, 1.0
                
            # Fuzzy match
            score = difflib.SequenceMatcher(None, query, target).ratio()
            
            if score > best_score:
                best_score = score
                best_match = existing
        
        if best_score >= self.threshold:
            return best_match, best_score
            
        return None, best_score
