"""
extraction_scratchpad.py — Cross-chunk structured note-taking (Pillar 4)

Implements the agentic scratchpad pattern from Anthropic's context engineering guide.
Accumulates established facts and resolved references across all 60+ chunk extractions,
injecting a compact <prior_context> block into each subsequent extractor call.

This prevents every chunk from starting cold with zero document-level awareness —
e.g., a Safety chunk already knowing "CLN-19, N=129, PTCL" without re-deriving it.

Pattern inspired by:
  - Claude Code's NOTES.md / to-do list approach
  - LangChain's "Life-Cycle Context" (how context evolves across the agent loop)

Usage:
    scratchpad = ExtractionScratchpad()
    # After each chunk extraction:
    scratchpad.update(chunk_result, section_type)
    # Before next chunk extraction:
    prior_ctx = scratchpad.get_context_injection(next_section_type)
    # Pass prior_ctx to PromptRegistry.get_system_prompt(section, prior_context=prior_ctx)
"""

import json
import os
from typing import List, Optional, Dict, Any


class ExtractionScratchpad:
    """
    Maintains a live, structured notes object that grows during the pipeline run.
    Thread-safe for concurrent reads; updates should be serialized by the caller.

    State structure mirrors the most important cross-section facts:
      - established_facts: confirmed doc-level data (drug name, study IDs, indication)
      - running_ae_list: accumulating adverse event names
      - resolved_references: table/section number → chunk context
      - unresolved_references: references seen but not yet located
      - extraction_counts: per-field extraction tally for diagnostic coverage
    """

    def __init__(self, persist_path: Optional[str] = None):
        """
        Args:
            persist_path: Optional file path to save/load scratchpad state.
                         Enables resumability across pipeline restarts.
        """
        self.persist_path = persist_path
        self._state: Dict[str, Any] = {
            "established_facts": {
                "drug_name": "Belinostat",               # Known before any extraction
                "drug_class": "Pan-HDAC inhibitor",
                "indication": None,
                "pivotal_study": None,
                "sponsor": None,
                "study_ids": [],
                "document_type": "Investigator Brochure",
            },
            "confirmed_values": {
                # Ground-truth values locked in as they are found — subsequent chunks can't override
                "orr": None,
                "median_pfs": None,
                "median_os": None,
                "elimination_half_life": None,
                "plasma_protein_binding": None,
                "metabolism_pathway": None,
                "dose_level": None,
                "dose_schedule": None,
            },
            "running_ae_list": [],            # MedDRA terms seen so far
            "resolved_references": {},        # "Table 2" → brief description
            "unresolved_references": [],      # References mentioned but not located yet
            "sections_processed": [],         # Ordered list of section types processed
            "extraction_counts": {},          # section_type → number of chunks processed
        }

        # Load from disk if resuming
        if persist_path and os.path.exists(persist_path):
            self._load(persist_path)

    # ─────────────────────────────────────────────────────────────────────────
    # Core API
    # ─────────────────────────────────────────────────────────────────────────

    def update(self, chunk_result: Dict[str, Any], section_type: str):
        """
        Update the scratchpad state from a completed chunk extraction result.

        Args:
            chunk_result: The dict returned by dili_extractor._extract_chunk()
            section_type: The section label for the processed chunk
        """
        if not chunk_result:
            return

        # Track section processing order
        if section_type not in self._state["sections_processed"]:
            self._state["sections_processed"].append(section_type)
        self._state["extraction_counts"][section_type] = (
            self._state["extraction_counts"].get(section_type, 0) + 1
        )

        # ── Study metadata facts ──────────────────────────────────────────
        meta = chunk_result.get("study_metadata", {})
        if isinstance(meta, dict):
            # Accumulate study IDs (union — never overwrite)
            new_ids = meta.get("study_identifiers", []) or []
            existing_ids = self._state["established_facts"]["study_ids"]
            for sid in new_ids:
                if sid and sid not in existing_ids:
                    existing_ids.append(sid)

            # Lock-in first-found values (don't overwrite established facts)
            self._set_if_missing("established_facts", "indication",
                                  meta.get("disease_indication") or 
                                  chunk_result.get("population_characteristics", {}).get("disease_indication"))
            self._set_if_missing("established_facts", "sponsor", meta.get("sponsor_information"))
            self._set_if_missing("established_facts", "pivotal_study", meta.get("study_group_classification"))

        # ── Efficacy confirmed values ─────────────────────────────────────
        efficacy = chunk_result.get("efficacy_outcomes", {})
        if isinstance(efficacy, dict):
            self._set_if_missing("confirmed_values", "orr", efficacy.get("objective_response_rate"))
            self._set_if_missing("confirmed_values", "median_pfs", efficacy.get("median_pfs"))
            self._set_if_missing("confirmed_values", "median_os", efficacy.get("median_os"))

        # ── PK confirmed values ───────────────────────────────────────────
        pk = chunk_result.get("pharmacokinetics", {})
        if isinstance(pk, dict):
            self._set_if_missing("confirmed_values", "elimination_half_life",
                                  pk.get("elimination_half_life"))
            self._set_if_missing("confirmed_values", "plasma_protein_binding",
                                  pk.get("plasma_protein_binding"))
            self._set_if_missing("confirmed_values", "metabolism_pathway",
                                  pk.get("metabolism_pathway"))

        # ── Dosing facts ──────────────────────────────────────────────────
        dosing = chunk_result.get("dosing_administration", {})
        if isinstance(dosing, dict):
            level = dosing.get("dose_level")
            unit = dosing.get("dose_unit")
            if level:
                dose_str = f"{level} {unit}".strip() if unit else level
                self._set_if_missing("confirmed_values", "dose_level", dose_str)
            self._set_if_missing("confirmed_values", "dose_schedule", dosing.get("dosing_schedule"))

        # ── Running AE list ───────────────────────────────────────────────
        # Handle both dict (BelinoIBExtractionSchema) and list (SafetyExtraction)
        safety = chunk_result.get("safety_data", chunk_result.get("adverse_events", []))
        ae_list = []
        if isinstance(safety, dict):
            ae_list = safety.get("adverse_events", [])
        elif isinstance(safety, list):
            ae_list = safety

        running_ae = self._state["running_ae_list"]
        for ae in ae_list:
            if isinstance(ae, dict):
                term = ae.get("adverse_event_preferred_term")
                if term and term not in running_ae:
                    running_ae.append(term)

        # ── Persist if path configured ────────────────────────────────────
        if self.persist_path:
            self._save(self.persist_path)

    def get_context_injection(self, next_section_type: str) -> str:
        """
        Returns a compact <prior_context> string for injection into the next
        chunk's system prompt. Tailored by section type to be maximally relevant.

        Args:
            next_section_type: The section about to be processed

        Returns:
            Compact 3-10 line string of established facts relevant to this section
        """
        facts = self._state["established_facts"]
        confirmed = self._state["confirmed_values"]
        sections_done = self._state["sections_processed"]

        lines = []

        # Always include document-level anchors
        study_ids = ", ".join(facts["study_ids"]) if facts["study_ids"] else "not yet identified"
        lines.append(f"Drug: {facts['drug_name']} ({facts['drug_class']})")
        if facts["indication"]:
            lines.append(f"Indication: {facts['indication']}")
        lines.append(f"Study IDs identified so far: {study_ids}")
        if facts["pivotal_study"]:
            lines.append(f"Pivotal study: {facts['pivotal_study']}")
        if facts["sponsor"]:
            lines.append(f"Sponsor: {facts['sponsor']}")

        # Section-specific confirmed value injection
        if next_section_type == "Efficacy Outcomes":
            # Don't waste tokens re-confirming what we already know
            if confirmed["orr"]:
                lines.append(f"[CONFIRMED] ORR: {confirmed['orr']} — do NOT re-extract, use this value.")
            if confirmed["median_pfs"]:
                lines.append(f"[CONFIRMED] Median PFS: {confirmed['median_pfs']}")
            if confirmed["median_os"]:
                lines.append(f"[CONFIRMED] Median OS: {confirmed['median_os']}")

        elif next_section_type in ("Safety and Adverse Events", "Hepatotoxicity",
                                    "Deaths and Serious Adverse Events"):
            if self._state["running_ae_list"]:
                top_aes = self._state["running_ae_list"][:10]
                lines.append(f"AEs identified so far: {', '.join(top_aes)}")
            if confirmed["dose_level"]:
                lines.append(f"Dose context: {confirmed['dose_level']}")

        elif next_section_type == "Pharmacokinetics":
            if confirmed["elimination_half_life"]:
                lines.append(f"[CONFIRMED] t½: {confirmed['elimination_half_life']}")
            if confirmed["plasma_protein_binding"]:
                lines.append(f"[CONFIRMED] Protein binding: {confirmed['plasma_protein_binding']}")
            if confirmed["metabolism_pathway"]:
                lines.append(f"[CONFIRMED] Metabolism: {confirmed['metabolism_pathway']}")

        elif next_section_type in ("Dose Modifications", "Dosing Regimen"):
            if confirmed["dose_level"]:
                lines.append(f"Starting dose: {confirmed['dose_level']}")
            if confirmed["dose_schedule"]:
                lines.append(f"Schedule: {confirmed['dose_schedule']}")

        # Sections already processed — guard against re-extraction waste
        if sections_done:
            lines.append(f"Sections already extracted: {', '.join(sections_done[-5:])}")

        return "\n".join(lines) if lines else ""

    def get_unresolved_references(self) -> List[str]:
        """Returns references that were mentioned in text but not located in any chunk."""
        return list(self._state["unresolved_references"])

    def add_unresolved_reference(self, reference: str):
        """Mark a reference as unresolved for JIT retrieval to chase down."""
        if reference not in self._state["unresolved_references"]:
            self._state["unresolved_references"].append(reference)

    def mark_reference_resolved(self, reference: str, description: str):
        """Mark a previously unresolved reference as found."""
        self._state["resolved_references"][reference] = description
        if reference in self._state["unresolved_references"]:
            self._state["unresolved_references"].remove(reference)

    def get_snapshot(self) -> Dict[str, Any]:
        """Returns a copy of the full scratchpad state (for debugging/logging)."""
        return dict(self._state)

    def get_established_facts(self) -> Dict[str, Any]:
        """Returns just the established facts subset."""
        return dict(self._state["established_facts"])

    def get_confirmed_values(self) -> Dict[str, Any]:
        """Returns confirmed clinical values."""
        return {k: v for k, v in self._state["confirmed_values"].items() if v is not None}

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _set_if_missing(self, state_key: str, field: str, value: Any):
        """Set a nested state field only if it is currently None/empty."""
        if value and not self._state[state_key].get(field):
            self._state[state_key][field] = value

    def _save(self, path: str):
        """Persist scratchpad state to disk as JSON."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            print(f"[Scratchpad] Warning: could not persist to {path}: {e}")

    def _load(self, path: str):
        """Load scratchpad state from disk."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Merge into default state (handles schema additions gracefully)
            for key, value in loaded.items():
                if key in self._state:
                    self._state[key] = value
            print(f"[Scratchpad] Resumed from {path}")
        except Exception as e:
            print(f"[Scratchpad] Warning: could not load from {path}: {e}")
