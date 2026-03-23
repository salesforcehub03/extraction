import pandas as pd
from typing import List, Dict, Any, Optional
import os

class TranscriptomicsLoader:
    """
    Loads and normalizes transcriptomics data (Gene Expression).
    Supports CSV/Excel input.
    """
    
    REQUIRED_COLUMNS = ["GeneID", "Symbol", "Log2FoldChange", "PValue", "Padj"]
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data: Optional[pd.DataFrame] = None
        
    def load(self) -> pd.DataFrame:
        """
        Loads the transcriptomics file and standardized columns.
        """
        if not os.path.exists(self.file_path):
            print(f"Transcriptomics file not found: {self.file_path}")
            return pd.DataFrame()
            
        try:
            if self.file_path.endswith('.csv'):
                df = pd.read_csv(self.file_path)
            else:
                df = pd.read_excel(self.file_path)
                
            # Normalize column names (basic)
            df.columns = [c.strip() for c in df.columns]
            
            # Smart Column Mapping (if exact names don't match)
            column_map = {}
            for col in df.columns:
                lower_col = col.lower()
                if "symbol" in lower_col or "gene name" in lower_col:
                    column_map[col] = "Symbol"
                elif "fold change" in lower_col or "log2fc" in lower_col:
                    column_map[col] = "Log2FoldChange"
                elif "p-value" in lower_col or "pvalue" in lower_col:
                    column_map[col] = "PValue"
                elif "adj" in lower_col or "fdr" in lower_col:
                    column_map[col] = "Padj"
                elif "id" in lower_col and "gene" in lower_col:
                    column_map[col] = "GeneID"
            
            df = df.rename(columns=column_map)
            self.data = df
            print(f"Loaded {len(df)} genes from transcriptomics data.")
            return df
            
        except Exception as e:
            print(f"Error loading transcriptomics: {e}")
            return pd.DataFrame()

    def get_significant_genes(self, p_adj_threshold: float = 0.05, logfc_threshold: float = 1.0) -> List[Dict[str, Any]]:
        """
        Returns list of significant genes as dictionaries.
        """
        if self.data is None:
            return []
            
        # Filter
        try:
            sig_df = self.data[
                (self.data["Padj"] < p_adj_threshold) & 
                (abs(self.data["Log2FoldChange"]) >= logfc_threshold)
            ]
            
            # Convert to list of dicts
            return sig_df.to_dict(orient="records")
        except KeyError as e:
            print(f"Missing required columns for filtering: {e}")
            return []

if __name__ == "__main__":
    # Test with dummy data
    pass
