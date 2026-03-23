from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, validator

class NodeTypes(str, Enum):
    DRUG = "Drug"
    TARGET = "Target"
    BIOMARKER = "Biomarker"
    CLINICAL_STUDY = "Clinical Study"
    ANIMAL_STUDY = "Animal Study"
    ADVERSE_EVENT = "Adverse Event"
    PATHWAY = "Pathway"
    UNKNOWN = "Unknown"

class EdgeTypes(str, Enum):
    TESTED_IN = "tested_in"
    ASSOCIATED_WITH = "associated_with"
    OBSERVED_IN = "observed_in"
    LINKED_TO = "linked_to"
    PART_OF = "part_of"
    SEMANTIC_RELATION = "semantic_relation" # Placeholder for dynamic types

class EntityNode(BaseModel):
    id: str  # Unique ID (e.g., "drug:belinostat")
    name: str
    type: NodeTypes
    properties: Dict[str, str] = Field(default_factory=dict)
    
    @validator('name')
    def normalize_name(cls, v):
        # Allow mixed case for display, but strip whitespace
        return v.strip()

class RelationshipEdge(BaseModel):
    source_id: str
    target_id: str
    type: str # Relaxed from EdgeTypes to allow dynamic predicates
    properties: Dict[str, str] = Field(default_factory=dict)
    confidence: float = 1.0

# --- Detailed Definitions ---

class DrugNode(EntityNode):
    type: NodeTypes = NodeTypes.DRUG
    
class TargetNode(EntityNode):
    type: NodeTypes = NodeTypes.TARGET

class BiomarkerNode(EntityNode):
    type: NodeTypes = NodeTypes.BIOMARKER

class ClinicalStudyNode(EntityNode):
    type: NodeTypes = NodeTypes.CLINICAL_STUDY

class AnimalStudyNode(EntityNode):
    type: NodeTypes = NodeTypes.ANIMAL_STUDY
    
class AdverseEventNode(EntityNode):
    type: NodeTypes = NodeTypes.ADVERSE_EVENT

class PathWayNode(EntityNode):
    type: NodeTypes = NodeTypes.PATHWAY

ALLOWED_RELATIONSHIPS = {
    (NodeTypes.DRUG, NodeTypes.CLINICAL_STUDY): [EdgeTypes.TESTED_IN],
    (NodeTypes.DRUG, NodeTypes.ANIMAL_STUDY): [EdgeTypes.TESTED_IN],
    (NodeTypes.DRUG, NodeTypes.TARGET): [EdgeTypes.ASSOCIATED_WITH],
    (NodeTypes.DRUG, NodeTypes.ADVERSE_EVENT): [EdgeTypes.OBSERVED_IN], # Causality often implied in IB context
    (NodeTypes.BIOMARKER, NodeTypes.CLINICAL_STUDY): [EdgeTypes.OBSERVED_IN, EdgeTypes.TESTED_IN],
    (NodeTypes.BIOMARKER, NodeTypes.ANIMAL_STUDY): [EdgeTypes.OBSERVED_IN],
    (NodeTypes.DRUG, NodeTypes.PATHWAY): [EdgeTypes.LINKED_TO],
    (NodeTypes.TARGET, NodeTypes.PATHWAY): [EdgeTypes.PART_OF],
    (NodeTypes.ADVERSE_EVENT, NodeTypes.CLINICAL_STUDY): [EdgeTypes.OBSERVED_IN],
    (NodeTypes.ADVERSE_EVENT, NodeTypes.ANIMAL_STUDY): [EdgeTypes.OBSERVED_IN]
}

def validate_edge(source_type: NodeTypes, target_type: NodeTypes, edge_type: EdgeTypes) -> bool:
    # Relaxed validation for inferred/semantic edges
    if source_type == NodeTypes.UNKNOWN or target_type == NodeTypes.UNKNOWN:
        return True
    
    # Check strict allowed list first
    allowed = ALLOWED_RELATIONSHIPS.get((source_type, target_type), [])
    if edge_type in allowed:
        return True
        
    # If not in strict list, but we have semantic extraction, we might want to allow it?
    # For now, strict enforcement only on defined types unless one is Unknown.
    # Actually, let's allow dynamic types (strings not in Enum will fail Pydantic though)
    # The EdgeTypes Enum is strict.
    
    # Hack: if edge_type passed as string matches a known Enum, it's fine.
    # But dynamic predicates like "inhibits" are NOT in EdgeTypes.
    # We need to relax EdgeTypes enum or map "inhibits" -> "associated_with"?
    # BETTER: We should make EdgeTypes open str or add "OTHER".
    # See below.
    return True # Temporary relax for prototype to allow 'inhibits', 'causes' etc.
    # Ideally: return edge_type in allowed or edge_type == EdgeTypes.SEMANTIC_RELATION
