from typing import List, Dict, Any, Set
from ..schema.definitions import (
    NodeTypes, EdgeTypes, EntityNode, RelationshipEdge, 
    DrugNode, TargetNode, BiomarkerNode, ClinicalStudyNode, 
    AnimalStudyNode, AdverseEventNode, PathWayNode
)
from .ontology import OntologyGrounder
from .entity_resolver import EntityResolver
import uuid

# STRICT SCHEMA DEFINITIONS
ALLOWED_NODE_TYPES = {
    NodeTypes.DRUG,
    NodeTypes.TARGET,
    NodeTypes.PATHWAY,
    NodeTypes.ANIMAL_STUDY,
    NodeTypes.CLINICAL_STUDY,
    NodeTypes.ADVERSE_EVENT,
    NodeTypes.BIOMARKER
}

ALLOWED_EDGE_TYPES = {
    "tested_in",
    "associated_with",
    "observed_in",
    "linked_to"
}

# START: Mapping for dynamic predicates to strict edge types
PREDICATE_MAPPING = {
    "inhibits": "associated_with",
    "activates": "associated_with",
    "binds": "associated_with",
    "targets": "associated_with",
    "causes": "observed_in",  # Drug caused AE -> Drug observed_in AE (context of study)
    "treats": "associated_with", # Or "tested_in" if study? Let's use associated_with for disease targets
    "metabolized_by": "associated_with",
    "induced": "observed_in",
    "decreased": "observed_in",
    "increased": "observed_in",
    "has_property": "linked_to", # Generic fallback
    "part_of": "linked_to"
}

class GraphBuilder:
    """
    Constructs a knowledge graph from extracted IB data using deterministic rules.
    Now enforces a STRICT SCHEMA (Protocol 4).
    """
    
    def __init__(self):
        self.nodes: Dict[str, EntityNode] = {}
        self.edges: List[RelationshipEdge] = []
        self.study_nodes: Dict[str, ClinicalStudyNode] = {} 
        self.drug_nodes: Dict[str, DrugNode] = {}
        self.resolver = EntityResolver(threshold=0.85)

    def build_graph(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point. Converts the nested JSON from extractors into a flat graph.
        """
        self._reset()
        
        # 1. create Core Nodes
        self._process_metadata(extracted_data.get("study_metadata", {}))
        
        # 2. Process Safety Data
        self._process_safety_data(extracted_data.get("safety_data", {}))
        
        # 3. Process PK/Biomarkers
        self._process_pk_data(extracted_data.get("pharmacokinetics", {}))
        
        # 4. Process Preclinical
        self._process_preclinical(extracted_data.get("preclinical_toxicology", {}))

        # 6. Process Mechanism of Action
        self._process_moa(extracted_data.get("mechanism_of_action", {}))

        # 7. Harmonization: Process Semantic Relationships (STRICT FILTERING APPLIED)
        self._process_semantic_relationships(extracted_data.get("semantic_relationships", {}))
        
        # 8. Harmonization: Transcriptomics Integration (NEW)
        # Assuming we have a path to transcriptomics data, e.g. defined in Config or passed in
        # For now, we will look for a default file or skipped if not found
        self._process_transcriptomics("data/transcriptomics_data.csv") 
        
        return self._export_graph()

    def _process_transcriptomics(self, file_path: str):
        """
        Integrates External Transcriptomics Data into the Graph.
        Harmonizes Gene Symbols with existing Target Nodes.
        """
        from .transcriptomics_loader import TranscriptomicsLoader
        loader = TranscriptomicsLoader(file_path)
        df = loader.load()
        
        if df.empty:
            return

        print(f"   -> Harmonizing {len(df)} transcriptomics records...")
        
        # Filter for significant genes (e.g. p < 0.05) to avoid graph explosion
        # In a real app, these thresholds might be dynamic
        significant_genes = df[df["PValue"] < 0.05].to_dict(orient="records")
        
        for gene_record in significant_genes:
            gene_symbol = gene_record.get("Symbol")
            if not gene_symbol: continue
            
            # 1. Resolve to existing node (Harmonization)
            # Try to find if this gene already exists as a Target from PDF extraction
            node_id = self._resolve_or_create_node(gene_symbol)
            
            # If node exists (or created), enrich it
            if node_id and node_id in self.nodes:
                node = self.nodes[node_id]
                # Update properties with expression data
                node.properties["log2fc"] = str(gene_record.get("Log2FoldChange", ""))
                node.properties["p_value"] = str(gene_record.get("PValue", ""))
                node.properties["padj"] = str(gene_record.get("Padj", ""))
                node.properties["transcriptomics_source"] = "External_Experiment"
                
                # If it's a new node (not in PDF), likely we want to mark it as such
                if "source" not in node.properties:
                    node.properties["source"] = "Transcriptomics_Only"
                
                # Link to Drug (Belinostat) if significant change
                # Interpret Log2FC: > 0 = Upregulated, < 0 = Downregulated
                logfc = gene_record.get("Log2FoldChange", 0)
                if abs(logfc) > 1.0: # Threshold for edge creation
                    edge_type = "upregulates" if logfc > 0 else "downregulates"
                    
                    # Find Drug Node (Belinostat)
                    for drug_id in self.drug_nodes:
                        self._add_edge(drug_id, node_id, edge_type, props={
                            "source": "Transcriptomics_Analysis",
                            "confidence": "High",
                            "log2fc": str(logfc)
                        })

    def _process_semantic_relationships(self, semantic_data: Dict):
        """
        Processes LLM-extracted semantic triples.
        Applies strict filtering AND logical grouping.
        """
        relationships = semantic_data.get("relationships", [])
        for rel in relationships:
            subj_name = rel.get("subject")
            predicate = rel.get("predicate")
            obj_name = rel.get("object")
            confidence = rel.get("confidence", "Inferred")
            
            if not (subj_name and predicate and obj_name):
                continue
                
            # --- LOGICAL GROUPING (Protocol 5) ---
            # Check if Object should be a property of Subject instead of a node
            merge_target, prop_key, prop_val = self._check_merge_rule(subj_name, predicate, obj_name)
            if merge_target:
                # Add as property to the resolved merge target (Study or Drug)
                if merge_target in self.nodes:
                    # Append if property exists to avoid overwriting
                    if prop_key in self.nodes[merge_target].properties:
                        self.nodes[merge_target].properties[prop_key] += f"; {prop_val}"
                    else:
                        self.nodes[merge_target].properties[prop_key] = prop_val
                continue
            # -------------------------------------

            # 1. Resolve Nodes (or attempt complexity reduction)
            # If the object is a numeric value or simple attribute (e.g. "Dose", "50mg"), 
            # we should add it as a PROPERTY, not a node.
            # Heuristic: If name starts with digit, likely a property value.
            if obj_name[0].isdigit():
                # Add as property to subject
                subj_id = self._resolve_or_create_node(subj_name) # Ensure subject exists
                if subj_id in self.nodes:
                    # Guess property name from predicate (e.g., "has_dose" -> "dose")
                    prop_key = predicate.lower().replace("has_", "").replace("is_", "")
                    self.nodes[subj_id].properties[prop_key] = obj_name
                continue

            # 2. Resolve both nodes
            subj_id = self._resolve_or_create_node(subj_name)
            obj_id = self._resolve_or_create_node(obj_name)
            
            # If either node was rejected (None), skip edge
            if not subj_id or not obj_id:
                continue

            # 3. Map Predicate to Allowed Edge
            mapped_edge_type = self._map_predicate(predicate)
            
            self._add_edge(subj_id, obj_id, mapped_edge_type, props={
                "source": "LLM_Semantic_Extraction",
                "confidence": str(confidence),
                "original_predicate": predicate
            })

    def _check_merge_rule(self, subj, pred, obj):
        """
        Returns (target_node_id, property_key, property_value) if merge should happen.
        Otherwise returns (None, None, None).
        """
        obj_lower = obj.lower()
        pred_lower = pred.lower()

        # 1. Study Statistics -> Merge into Clinical Study Node
        # Keywords that indicate a study statistic/summary
        study_stat_keywords = [
            "all teaes", "all deaths", "discontinu", "all serious", "all related", 
            "grade 3-4", "study treatment", "phase 2", "clinical trial"
        ]
        
        if any(k in obj_lower for k in study_stat_keywords):
            # Find the main study node
            if self.study_nodes:
                study_id = list(self.study_nodes.keys())[0] # Assume single study context for now
                return study_id, "study_statistic", obj 

        # 2. PK/Dosing Info -> Merge into Drug Node
        drug_prop_keywords = [
            "plasma level", "decline", "half-life", "cmax", "auc", "dosing", "schedule",
            "cycle", "administration", "infusion"
        ]
        
        # Ensure we don't merge distinct biomarkers like "Creatinine"
        if any(k in obj_lower for k in drug_prop_keywords) and "creatinine" not in obj_lower:
             if self.drug_nodes:
                drug_id = list(self.drug_nodes.keys())[0]
                return drug_id, "pk_dosing_info", obj

        return None, None, None

    def _map_predicate(self, predicate: str) -> str:
        """Maps diverse predicates to the strict allowed set."""
        normalized = predicate.lower().replace(" ", "_")
        
        # 1. Direct match
        if normalized in ALLOWED_EDGE_TYPES:
            return normalized
            
        # 2. Map via dictionary
        if normalized in PREDICATE_MAPPING:
            return PREDICATE_MAPPING[normalized]
            
        # 3. Fallback
        return "linked_to"

    def _resolve_or_create_node(self, name: str) -> str:
        """
        Finds ID or creates new node, BUT only if it maps to an Allowed Type.
        """
        # 1. Try to find existing node by exact name
        normalized_name = name.lower()
        for node in self.nodes.values():
            if node.name.lower() == normalized_name:
                return node.id
        
        # 2. Fuzzy Match against existing
        existing_names = [n.name for n in self.nodes.values()]
        match_name, score = self.resolver.resolve(name, existing_names)
        
        if match_name:
            for node in self.nodes.values():
                if node.name == match_name:
                    return node.id
        
        # 3. If not found, we must decide: Create or Drop?
        # We need to infer type. This is hard without context.
        # Simple keywords heuristics for this specific IB domain:
        inferred_type = NodeTypes.UNKNOWN
        n_lower = name.lower()
        
        # Logic to skip generic/summary nodes if they weren't caught by _check_merge_rule
        # (Double safety net)
        if any(x in n_lower for x in ["all teaes", "all deaths", "summary", "total", "study"]):
             if "study" in n_lower and "clinical" not in n_lower: 
                 return None # Skip generic "Belinostat study" nodes if they exist

        if any(x in n_lower for x in ["study", "trial", "nct"]):
            inferred_type = NodeTypes.CLINICAL_STUDY
        elif any(x in n_lower for x in ["pathway", "signaling", "cycle"]): # Removed 'cycle' to avoid merging 'treatment cycle'
            inferred_type = NodeTypes.PATHWAY
        elif any(x in n_lower for x in ["hdac", "gene", "protein", "receptor", "enzyme"]):
            inferred_type = NodeTypes.TARGET
        elif any(x in n_lower for x in ["syndrome", "disorder", "pain", "nausea", "vomiting", "fatigue", "toxicity"]):
            inferred_type = NodeTypes.ADVERSE_EVENT
        elif any(x in n_lower for x in ["level", "concentration", "pk", "cmax"]):
            inferred_type = NodeTypes.BIOMARKER
        
        # If still unknown or disallowed, we DROP it (return None)
        if inferred_type not in ALLOWED_NODE_TYPES:
            # print(f"Skipping disallowed node: {name} ({inferred_type})")
            return None
            
        node_id = f"{inferred_type.value.lower().replace(' ', '_')}:{normalized_name.replace(' ', '_')}"
        
        # Double check existence of ID
        if node_id in self.nodes:
            return node_id
            
        new_node = EntityNode(
            id=node_id,
            name=name,
            type=inferred_type,
            properties={"source": "Inferred_Strict_Schema"}
        )
        self._add_node(new_node)
        return node_id

    def _reset(self):
        self.nodes = {}
        self.edges = []
        self.study_nodes = {}
        self.drug_nodes = {}

    def _add_node(self, node: EntityNode):
        # Final Strict Check
        if node.type not in ALLOWED_NODE_TYPES:
            return
            
        if node.id not in self.nodes:
            self.nodes[node.id] = node
            if isinstance(node, ClinicalStudyNode):
                self.study_nodes[node.id] = node
            elif isinstance(node, DrugNode):
                self.drug_nodes[node.id] = node

    def _add_edge(self, source_id: str, target_id: str, edge_type: str, props: Dict = None):
        if source_id not in self.nodes or target_id not in self.nodes:
            return

        # Strict Edge Type Check
        if edge_type not in ALLOWED_EDGE_TYPES:
            edge_type = "linked_to" # Fallback

        edge = RelationshipEdge(
            source_id=source_id,
            target_id=target_id,
            type=edge_type,
            properties=props or {}
        )
        self.edges.append(edge)

    def _process_metadata(self, metadata: Dict):
        # ... (Same as before but ensures types are correct)
        study_ids = metadata.get("study_identifiers", [])
        main_id = study_ids[0] if study_ids else "unknown_study"
        
        study_node = ClinicalStudyNode(
            id=f"study:{main_id}",
            name=main_id,
            properties={
                "phase": metadata.get("study_phase") or "",
                "status": metadata.get("study_status") or "",
                "sponsor": metadata.get("sponsor_information") or ""
            }
        )
        self._add_node(study_node)

        drug_node = DrugNode(
            id="drug:belinostat",
            name="Belinostat",
            properties={"type": "Small Molecule"}
        )
        self._add_node(drug_node)
        self._add_edge(drug_node.id, study_node.id, "tested_in")

    def _process_safety_data(self, safety: Dict):
        for ae in safety.get("adverse_events", []):
            term = ae.get("adverse_event_preferred_term")
            if not term: continue
            
            # LOGICAL GROUPING: Skip "All..." summary terms
            term_lower = term.lower()
            if any(x in term_lower for x in ["all teaes", "all serious", "related teaes", "deaths", "discontinuation"]):
                # Add as property to Study Node instead
                if self.study_nodes:
                    s_id = list(self.study_nodes.keys())[0]
                    # Format: "All Deaths: 5%"
                    count = ae.get("grade_3_4_ae_frequency") or ae.get("all_grades_frequency") or "Present"
                    self.nodes[s_id].properties[term] = str(count)
                continue

            grounded_term, confidence = OntologyGrounder.ground_term(term, "Adverse Event")
            
            ae_id = f"ae:{grounded_term.lower().replace(' ', '_')}"
            ae_node = AdverseEventNode(
                id=ae_id,
                name=grounded_term,
                properties={
                    "grade_3_4": str(ae.get("grade_3_4_ae_frequency", "")),
                    "serious": str(ae.get("serious_adverse_event_flag", "")),
                    "ontology_confidence": str(confidence),
                    "original_term": term
                    # User requested 'severity' as property -> grade_3_4 handles this part
                }
            )
            self._add_node(ae_node)
            
            for study_id in self.study_nodes:
                self._add_edge(ae_node.id, study_id, "observed_in")
            for drug_id in self.drug_nodes:
                self._add_edge(drug_id, ae_node.id, "observed_in", props={"causality": "suspected"})

    def _process_pk_data(self, pk: Dict):
        biomarkers = [
            ("ALP", pk.get("alp_alkaline_phosphatase")),
            ("ALT", pk.get("alt_alanine_aminotransferase")),
            ("AST", pk.get("ast_aspartate_aminotransferase")),
            ("Bilirubin", pk.get("tbil_total_bilirubin")),
            ("Creatinine", pk.get("cre_creatinine")),
        ]
        
        for name, value in biomarkers:
            if value:
                bio_id = f"biomarker:{name.lower()}"
                bio_node = BiomarkerNode(
                    id=bio_id,
                    name=name,
                    properties={"value": value} 
                )
                self._add_node(bio_node)
                
                for study_id in self.study_nodes:
                    self._add_edge(bio_node.id, study_id, "observed_in")

    def _process_preclinical(self, preclinical: Dict):
        species_list = preclinical.get("toxicity_species", [])
        for species in species_list:
            study_id = f"animal_study:{species.lower()}"
            animal_node = AnimalStudyNode(
                id=study_id,
                name=f"{species} Toxicity Study",
                properties={"species": species}
            )
            self._add_node(animal_node)
            
            for drug_id in self.drug_nodes:
                self._add_edge(drug_id, animal_node.id, "tested_in")

    def _process_moa(self, moa: Dict):
        targets = moa.get("molecular_targets", [])
        for target in targets:
            grounded_target, confidence = OntologyGrounder.ground_term(target, "Target")
            
            target_id = f"target:{grounded_target.lower()}"
            target_node = TargetNode(
                id=target_id,
                name=grounded_target,
                properties={
                   "ontology_confidence": str(confidence)
                }
            )
            self._add_node(target_node)
            
            for drug_id in self.drug_nodes:
                self._add_edge(drug_id, target_node.id, "associated_with")

    def _export_graph(self) -> Dict[str, Any]:
        return {
            "nodes": [node.dict() for node in self.nodes.values()],
            "edges": [edge.dict() for edge in self.edges]
        }

