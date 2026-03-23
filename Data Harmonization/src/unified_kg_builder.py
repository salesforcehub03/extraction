"""
Unified Knowledge Graph Builder for Data Harmonization
Combines functionality from:
- belino_kg_builder.py (Core Logic)
- glimpse_excel.py (Inspection Tool)
- graph_schema.py (Data Structures)

Usage:
    python unified_kg_builder.py --build       # Run harmonization
    python unified_kg_builder.py --validate    # Validate output
    python unified_kg_builder.py --glimpse     # Inspect input files
    python unified_kg_builder.py               # Run build & validate (default)
"""

import pandas as pd
import json
import os
import math
import argparse
import sys
import glob
import hashlib
import traceback
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
import numpy as np

# --- CONFIGURATION ---
# Paths from belino_kg_builder.py (Most recent active config)
BASE_DIR = r"D:\AViiD"
BELINO_GENE_DIR = os.path.join(BASE_DIR, "belino-gene")
INPUT_FILES_DIR = os.path.join(BASE_DIR, "Input files")
OUTPUT_DIR = os.path.join(BASE_DIR, "Data Harmonization")

META_FILE = os.path.join(BELINO_GENE_DIR, "meta_sigSearch_LIB_5_2026_2_13_13_16_31.xls")
SIG_FILE = os.path.join(BELINO_GENE_DIR, "sig_Fri_Feb_13_08_12_35_2026_5800759.xls")
CONSOLIDATED_FILE = os.path.join(INPUT_FILES_DIR, "belino_comprehensive_consolidated.xlsx")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "belino_refined_kb.json")


# --- DATA STRUCTURES (from graph_schema.py) ---

@dataclass
class Node:
    """Represents a node in the knowledge graph"""
    id: str
    type: str
    properties: Dict[str, Any]
    source_file: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "properties": self.properties,
            "source_file": self.source_file
        }

@dataclass
class Edge:
    """Represents an edge in the knowledge graph"""
    source: str
    target: str
    relation: str  # unified 'relation' vs 'type' naming
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "properties": self.properties
        }

@dataclass
class KnowledgeGraph:
    """Represents the complete knowledge graph"""
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)
    edge_hashes: set = field(default_factory=set)

    def add_node(self, node: Node):
        if node.id not in self.nodes:
            self.nodes[node.id] = node

    def add_edge(self, edge: Edge):
        # Create a unique hash for the edge to prevent duplicates
        edge_hash = f"{edge.source}|{edge.relation}|{edge.target}"
        if edge_hash not in self.edge_hashes:
            self.edges.append(edge)
            self.edge_hashes.add(edge_hash)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges]
        }

# --- HELPER FUNCTIONS ---

def generate_stable_id(node_type: str, *key_parts) -> str:
    """Generate a consistent ID based on content."""
    raw_id = f"{node_type}:" + ":".join(str(k) for k in key_parts if k)
    return f"{node_type}_{hashlib.sha256(raw_id.encode()).hexdigest()[:16]}"

def sanitize_value(val):
    """Clean string values, handling NaNs and whitespace."""
    if val is None: return None
    if isinstance(val, (float, np.float64)) and (math.isnan(val) or math.isinf(val)):
        return None
    s = str(val).strip()
    return None if s.lower() == 'nan' or s == '' else s

def clean_properties(props: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values from a dictionary."""
    return {k: v for k, v in props.items() if v is not None}


# --- GLIMPSE TOOL (from glimpse_excel.py) ---

def run_glimpse():
    print("\n=== RUNNING GLIMPSE TOOL ===")
    search_path = os.path.join(BELINO_GENE_DIR, "*.xls*")
    files = glob.glob(search_path)
    
    if not files:
        print(f"No Excel files found in {BELINO_GENE_DIR}")
        return

    for f in files:
        print(f"\n{'='*50}")
        print(f"File: {os.path.basename(f)}")
        
        methods = [
            ("pandas default", {}),
            ("engine='xlrd'", {'engine': 'xlrd'}),
            ("engine='openpyxl'", {'engine': 'openpyxl'}),
            ("read_csv (tab)", {'sep': '\t'}),
            ("read_csv (comma)", {'sep': ','})
        ]
        
        success = False
        for method_name, kargs in methods:
            try:
                if "read_csv" in method_name:
                    df = pd.read_csv(f, **kargs)
                else:
                    df = pd.read_excel(f, nrows=5, **kargs)
                
                print(f"Success with {method_name}")
                print(f"Columns: {df.columns.tolist()}")
                print(f"Shape: {df.shape}")
                print("-" * 20)
                print(df.head(3).to_string())
                success = True
                break
            except Exception:
                pass
        
        if not success:
            print("Failed to read file with available methods.")
    print("\n=== GLIMPSE COMPLETE ===\n")


# --- HARMONIZATION LOGIC (from belino_kg_builder.py) ---

def read_flexible(file_path):
    """Helper to read CSV or Excel files with robust fallback."""
    ext = os.path.splitext(file_path)[-1].lower()
    
    # Strategy 1: Try reading as Excel (auto, then specific engines)
    if ext in ['.xlsx', '.xls']:
        try:
            return pd.read_excel(file_path)
        except Exception:
            try:
                return pd.read_excel(file_path, engine='openpyxl')
            except Exception:
                try:
                    return pd.read_excel(file_path, engine='xlrd')
                except Exception:
                    print(f"Warning: Failed to read {file_path} as Excel. Trying text parse...")
                    # Fallthrough to text parsing (sometimes .xls are just TSVs)

    # Strategy 2: Text/CSV Parsing (Tab default, then comma)
    try:
        return pd.read_csv(file_path, sep='\t')
    except Exception:
        try:
            return pd.read_csv(file_path, sep=',')
        except Exception as e:
            raise ValueError(f"Could not read {file_path} as Excel or CSV/TSV. Error: {e}")

def load_data(custom_file=None, custom_meta=None, custom_sig=None, use_defaults=True):
    print("Loading input files...")
    
    meta_df = None
    sig_df = None

    # Metadata
    if custom_meta:
        if not os.path.exists(custom_meta): raise FileNotFoundError(f"Meta file not found: {custom_meta}")
        meta_df = read_flexible(custom_meta)
    elif use_defaults and os.path.exists(META_FILE):
        print(f"Using default Metadata: {META_FILE}")
        meta_df = read_flexible(META_FILE)
    else:
        print("Warning: No Metadata file provided. Skipping Transcriptomics.")
    
    # Signatures
    if custom_sig:
        if not os.path.exists(custom_sig): raise FileNotFoundError(f"Sig file not found: {custom_sig}")
        sig_df = read_flexible(custom_sig)
    elif use_defaults and os.path.exists(SIG_FILE):
        print(f"Using default Signatures: {SIG_FILE}")
        sig_df = read_flexible(SIG_FILE)
    else:
        print("Warning: No Signature file provided. Skipping Transcriptomics.")
    
    target_file = custom_file if custom_file else CONSOLIDATED_FILE
    print(f"Loading {target_file}...")
    
    if not os.path.exists(target_file):
        raise FileNotFoundError(f"Input file not found: {target_file}")

    xl = pd.ExcelFile(target_file)
    sheet_names = xl.sheet_names
    print(f"Found sheets: {sheet_names}")

    # Initialize containers
    drug_info_data = {} # Can be a DF (legacy) or Dict of DFs (new)
    safety_df = pd.DataFrame()
    data_format = "unknown"

    # DETECT FORMAT
    if '4. Drug Product Info' in sheet_names:
        print("-> Detected Legacy Format (Key-Value)")
        data_format = "legacy"
        drug_info_data = xl.parse('4. Drug Product Info')
        safety_sheet = '6. Adverse Events' if '6. Adverse Events' in sheet_names else None
        if safety_sheet: safety_df = xl.parse(safety_sheet)

    else:
        print("-> Detected New Extraction Format (Tabular)")
        data_format = "new"
        
        # 1. Load Adverse Events (Variable names)
        ae_sheet = next((s for s in sheet_names if "Adverse Events" in s), None)
        if ae_sheet:
            print(f"   Using AE Sheet: {ae_sheet}")
            safety_df = xl.parse(ae_sheet)
        
        # 2. Load All Other Sheets as Drug Info
        # We exclude AE sheets and known non-metadata sheets if any
        drug_sheets = [s for s in sheet_names if s != ae_sheet and "Safety" not in s]
        drug_info_data = {s: xl.parse(s) for s in drug_sheets}

    print(f"Loaded Metadata: {len(meta_df) if meta_df is not None else 0} rows")
    print(f"Loaded Signatures: {len(sig_df) if sig_df is not None else 0} rows")
    print(f"Data Format: {data_format}")
    
    return meta_df, sig_df, drug_info_data, safety_df, data_format

def harmonize(meta_df, sig_df, drug_info_data, safety_df, data_format="legacy") -> KnowledgeGraph:
    kg = KnowledgeGraph()
    
    # 1. Processing Metadata (Signatures)
    # 1. Processing Metadata (Signatures)
    print("Processing Metadata...")
    # Used to track the "Main Drug" for this analysis
    main_drug_name = "Belinostat" # Default fallback
    
    if meta_df is not None:
        for _, row in meta_df.iterrows():
            sig_id = sanitize_value(row.get('SignatureId'))
            drug_name = sanitize_value(row.get('Perturbagen'))
            
            if not sig_id or not drug_name: continue
            
            # Update main drug if found (heuristic)
            if drug_name: main_drug_name = drug_name
    
            # Drug Node
            if drug_name not in kg.nodes:
                props = clean_properties({
                    "lincspertid": sanitize_value(row.get('lincspertid')),
                    "perturbagenID": sanitize_value(row.get('perturbagenID')),
                    "pubChemID": sanitize_value(row.get('pubChemID')),
                    "stitchID": sanitize_value(row.get('stitchID'))
                })
                kg.add_node(Node(id=drug_name, type="Drug", properties=props, source_file="meta_sigSearch"))
                
            # Signature Node
            props = clean_properties({
                "concentration": sanitize_value(row.get('Concentration')),
                "time": sanitize_value(row.get('Time')),
                "factor": sanitize_value(row.get('factor')),
                "is_exemplar": sanitize_value(row.get('is_exemplar')),
                "cell_line": sanitize_value(row.get('CellLine')),
                "tissue": sanitize_value(row.get('Tissue')),
                "gene_targets": sanitize_value(row.get('GeneTargets')),
                # Redundant IDs also stored on Signature for reference
                "lincspertid": sanitize_value(row.get('lincspertid'))
            })
            kg.add_node(Node(id=sig_id, type="Transcriptomic_Signature", properties=props, source_file="meta_sigSearch"))
            
            kg.add_edge(Edge(source=drug_name, target=sig_id, relation="tested_in"))
            
            # CellLine Node
            cell_line = sanitize_value(row.get('CellLine'))
            if cell_line:
                kg.add_node(Node(id=cell_line, type="CellLine", properties={}, source_file="meta_sigSearch"))
                kg.add_edge(Edge(source=sig_id, target=cell_line, relation="observed_in"))
                
                # Tissue Node
                tissue = sanitize_value(row.get('Tissue'))
                if tissue:
                    tissue_id = tissue.lower()
                    kg.add_node(Node(id=tissue_id, type="Tissue", properties={"name": tissue}, source_file="meta_sigSearch"))
                    kg.add_edge(Edge(source=cell_line, target=tissue_id, relation="derived_from"))
    
            # Target Nodes
            targets_str = sanitize_value(row.get('GeneTargets'))
            if targets_str:
                for t_name in targets_str.split('|'):
                    t_name = t_name.strip()
                    if not t_name: continue
                    target_id = f"Target_{t_name}" 
                    kg.add_node(Node(id=target_id, type="Target", properties={"symbol": t_name}, source_file="meta_sigSearch"))
                    kg.add_edge(Edge(source=drug_name, target=target_id, relation="targets"))
    else:
        print("Skipping Metadata/Signature nodes (No Metadata provided).")

    # 2. Enrich Drug Node
    print(f"Enriching Drug Properties for {main_drug_name}...")
    
    # Ensure Main Drug Node exists (Critical for Clinical-Only mode)
    if main_drug_name not in kg.nodes:
        print(f"Creating base Drug node for {main_drug_name}...")
        kg.add_node(Node(id=main_drug_name, type="Drug", properties={"name": main_drug_name}, source_file="Inferred_Base"))

    belino_node = kg.nodes.get(main_drug_name)
    # Fallback to "Belinostat" if main_drug_name differed but we want to be safe
    if not belino_node: belino_node = kg.nodes.get("Belinostat")

    if belino_node:
        if data_format == "legacy":
            # LEGACY LOGIC: Iterate rows of Key/Value pairs
            for _, row in drug_info_data.iterrows():
                cat = sanitize_value(row.get('Category'))
                field_name = sanitize_value(row.get('Field'))
                val = sanitize_value(row.get('Value'))
                
                if field_name and val:
                    prop_key = f"{cat}_{field_name}".replace(" ", "_").replace("&", "and")
                    belino_node.properties[prop_key] = val
        
        elif data_format == "new":
            # NEW LOGIC: Iterate Sheets -> Columns -> Values
            # drug_info_data is a Dict[sheet_name, DataFrame]
            for sheet_name, df in drug_info_data.items():
                if df.empty: continue
                
                # Clean sheet name for prefix (e.g., "1. Study Metadata" -> "Study_Metadata")
                clean_sheet = sheet_name.split('. ')[-1].replace(" ", "_").replace("&", "and") if '. ' in sheet_name else sheet_name.replace(" ", "_")
                
                # Take the first row of data (assuming single drug context)
                first_row = df.iloc[0]
                
                for col_name, val in first_row.items():
                    val = sanitize_value(val)
                    if val is not None:
                        # e.g., Study_Metadata_Status
                        prop_key = f"{clean_sheet}_{col_name}".replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
                        belino_node.properties[prop_key] = val

    # 3. Process Adverse Events
    print("Processing Adverse Events...")
    if belino_node:
        for _, row in safety_df.iterrows():
            # Handle both Legacy ('AE Term') and New ('AE Term' from writer or mapped)
            # Checked comprehensive_excel_writer.py: it writes header ["AE Term", "Count", "%"...]
            
            ae_term = sanitize_value(row.get('AE Term'))
            if not ae_term: continue
            
            ae_id = f"AdverseEvent_{ae_term.replace(' ', '_')}"
            kg.add_node(Node(id=ae_id, type="AdverseEvent", properties={"name": ae_term}, source_file="consolidated_AE"))
                
            # Handle varied column names between formats if needed
            # Legacy: '%', 'Grade 3-4', 'SAE'
            # New: '%', 'Grade 3-4', 'SAE' (Writer seems to use similar headers, let's verify)
            
            edge_props = clean_properties({
                "frequency": sanitize_value(row.get('%')),
                "grade_3_4_count": sanitize_value(row.get('Grade 3-4')),
                "is_sae": sanitize_value(row.get('SAE') or row.get('is_sae')),
                "is_teae": sanitize_value(row.get('TEAE')) 
            })
            kg.add_edge(Edge(source=belino_node.id, target=ae_id, relation="causes", properties=edge_props))

    # 4. Process Signatures (Top 20 Genes)
    print("Processing Signatures (Top 20 per signature)...")
    if sig_df is not None:
        sig_groups = sig_df.groupby('signatureID')
        for sig_id, group in sig_groups:
            sig_id = sanitize_value(sig_id)
            if not sig_id or sig_id not in kg.nodes: continue
            
            # Calculate absolute logFC for sorting
            group['abs_logfc'] = group['Value_LogDiffExp'].abs()
            top_genes = group.sort_values('abs_logfc', ascending=False).head(20)
            
            for _, row in top_genes.iterrows():
                gene_symbol = sanitize_value(row.get('Name_GeneSymbol'))
                try:
                    log_fc = float(row.get('Value_LogDiffExp', 0.0))
                    p_val = float(row.get('Significance_pvalue', 1.0))
                except (ValueError, TypeError):
                    continue
                    
                if not gene_symbol: continue
                
                # Biomarker Node
                # Using gene symbol as ID for simplicity and uniqueness in this context
                if gene_symbol not in kg.nodes:
                    kg.add_node(Node(id=gene_symbol, type="Biomarker", properties={"gene": gene_symbol, "source": "signature_top_20"}))
                
                kg.add_edge(Edge(source=sig_id, target=gene_symbol, relation="associated_with", properties={
                    "log_fold_change": log_fc,
                    "p_value": p_val
                }))
    else:
        print("Skipping Signature Genes (No Signature file provided).")

    return kg


# --- VALIDATION LOGIC ---

def run_validation(target_file=OUTPUT_FILE):
    print("\n=== RUNNING VALIDATION ===")
    if not os.path.exists(target_file):
        print(f"Error: Output file {target_file} does not exist.")
        return

    try:
        with open(target_file, 'r') as f:
            data = json.load(f)
        
        nodes = data.get('nodes', [])
        edges = data.get('edges', [])
        node_map = {n['id']: n for n in nodes}
        
        print(f"Total Nodes: {len(nodes)}")
        print(f"Total Edges: {len(edges)}")
        
        # 1. Check Drug Node
        drugs = [n for n in nodes if n['type'] == 'Drug']
        if drugs:
            print(f"✓ Found {len(drugs)} Drug nodes.")
            belino = next((d for d in drugs if 'Belinostat' in d['id']), None)
            if belino:
                print(f"  - Belinostat Properties: {len(belino['properties'])}")
            else:
                print("  ! Warning: Belinostat node not explicitly found by ID.")
        else:
            print("✗ Error: No Drug nodes found!")
            
        # 2. Check Signature Integrity
        sigs = [n for n in nodes if n['type'] == 'Transcriptomic_Signature']
        print(f"✓ Found {len(sigs)} Signature nodes.")
        if sigs:
            sample_sig = sigs[0]
            print(f"  - Sample Signature ({sample_sig['id']}) properties: {list(sample_sig['properties'].keys())}")

        # 3. Check Edge Continuity
        lost_edges = [e for e in edges if e['source'] not in node_map or e['target'] not in node_map]
        if lost_edges:
            print(f"✗ Warning: {len(lost_edges)} edges have missing source/target nodes.")
        else:
            print("✓ All edges connect to valid nodes.")

    except Exception as e:
        print(f"Validation failed with error: {e}")
        traceback.print_exc()
        
    print("=== VALIDATION COMPLETE ===\n")


# --- MAIN ---

def main():
    parser = argparse.ArgumentParser(description="Unified Knowledge Graph Builder")
    parser.add_argument("--build", action="store_true", help="Run harmonization logic")
    parser.add_argument("--validate", action="store_true", help="Run validation checks")
    parser.add_argument("--glimpse", action="store_true", help="Run file inspection (glimpse) tool")
    parser.add_argument("--input_file", "-i", type=str, help="Override path to consolidated Excel file")
    parser.add_argument("--output_file", "-o", type=str, help="Override path to output JSON file")
    parser.add_argument("--meta_file", "-m", type=str, help="Override path to metadata file")
    parser.add_argument("--sig_file", "-s", type=str, help="Override path to signature file")
    
    # If no args provided, default to Build + Validate
    if len(sys.argv) == 1:
        args = parser.parse_args(['--build', '--validate'])
    else:
        args = parser.parse_args()

    if args.glimpse:
        run_glimpse()
    
    # Determine target output file
    target_output_file = args.output_file if args.output_file else OUTPUT_FILE
    
    if args.build:
        try:
            # If input_file is provided (via API/CLI), we do NOT want random defaults filling in gaps.
            # We want strict adherence to what was passed.
            use_defaults = (args.input_file is None)
            
            meta_df, sig_df, drug_info_data, safety_df, data_format = load_data(
                args.input_file, 
                args.meta_file, 
                args.sig_file, 
                use_defaults=use_defaults
            )
            
            # Log detected mode
            modes = []
            if len(drug_info_data) > 0 or not safety_df.empty: modes.append("CLINICAL/PRECLINICAL")
            if meta_df is not None: modes.append("TRANSCRIPTOMICS")
            print(f"\n✅ RECOGNIZED MODES: {' + '.join(modes)}")
            
            kg = harmonize(meta_df, sig_df, drug_info_data, safety_df, data_format)
            
            print(f"Saving {len(kg.nodes)} nodes and {len(kg.edges)} edges to {target_output_file}...")
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(target_output_file), exist_ok=True)
            
            with open(target_output_file, 'w') as f:
                json.dump(kg.to_dict(), f, indent=2)
            print("Build Complete.")
        except Exception as e:
            print(f"Build Failed: {e}")
            traceback.print_exc()
            sys.exit(1)

    if args.validate:
        # If validating, we need to know WHICH file to validate
        # We'll use the one we just built (if build was called) or the argument
        run_validation(target_output_file)

if __name__ == "__main__":
    main()
