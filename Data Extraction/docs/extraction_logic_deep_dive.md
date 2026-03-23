# Extraction Logic & Smart Chunking - Deep Dive

## Overview

Stage 3 is the engine of the system. It takes the parsed markdown and converts it into structured clinical data. The primary challenges are **document size** (overwhelming the LLM's context window) and **extraction speed**.

---

## 🏗️ The Problem: Context Window vs. Document Size

- **Document Size**: ~220,000 characters (approx. 50,000 - 60,000 tokens).
- **LLM Context Limit**: While Gemini has a large window, reliability decreases with extremely long prompts.
- **Solution**: **Smart Chunking** + **Async Parallel Extraction**.

---

## 1. Smart Chunking Strategy

**File:** [`src/dili_extractor.py`](file:///d:/AViiD/Team%201/src/dili_extractor.py)

We split the "Relevant Text" (filtered in Stage 2) into manageable pieces.

### Configuration
```python
self.CHUNK_SIZE = 4000  # ~1,000 tokens
self.OVERLAP = 500      # ~125 tokens overlap
```

### Why 4,000 characters?
- It's large enough to contain full tables or descriptive sections.
- It's small enough to ensure Gemini 2.0 Flash remains highly precise.
- It allows for massively parallel processing.

### Why 500 characters overlap?
- If a sentence or table row is split exactly at the 4,000-character mark, the **overlap** ensuring the context is captured in the next chunk.
- Without overlap, the LLM might see "ORR was" at the end of chunk 1 and "25.6%" at the start of chunk 2, failing to extract the value in either.

---

## 2. Async Parallel Extraction

This is why the pipeline runs so fast (~60 seconds for 220 pages).

### The Logic
Instead of processing chunk 1, then chunk 2, then chunk 3... we send them all at once.

```python
# Create tasks for all chunks
tasks = [self._extract_chunk(chunk) for chunk in chunks]

# Gather all results concurrently
results = await asyncio.gather(*tasks)
```

### Efficiency Gain
| Method | Time per Chunk | Total Chunks | Total Time |
| :--- | :--- | :--- | :--- |
| **Sequential** | ~2 seconds | 37 | **~74 seconds** |
| **Parallel (Async)** | ~2 seconds | 37 | **~3-5 seconds (Total LLM time)** |

---

## 3. Gemini 2.0 Flash & Pydantic

We use **GPT-4o** (via Azure OpenAI) because it provides superior accuracy and structured output capabilities.

### Pydantic Schema Enforcement
We don't just ask the LLM for "JSON". We provide a strict **Pydantic Model**.

**File:** [`src/schema.py`](file:///d:/AViiD/Team%201/src/schema.py)
```python
class DILIExtractionResult(BaseModel):
    study_metadata: StudyMetadata
    dosing_regimen: DosingRegimen
    efficacy_outcomes: EfficacyOutcomes
    # ... and 8 other detailed tables
```

### How LLM uses the Schema
When we call the Azure OpenAI API, we use function calling with the Pydantic schema converted to JSON Schema format. GPT-4o acts as a "Clinical Data Auditor" that fills in the structured slots with high precision.

---

## 4. Hierarchical Merging Strategy

Since each chunk only "sees" ~2% of the document, the extraction results are fragmented. We need to merge them back into a single unit.

### The Algorithm: `_merge_dicts`
The aggregator recursively walks through the 37 different JSON outputs and combines them:

1. **Lists (Tables)**:
   - Does "Study CLN-19" exist in the list already?
   - If **No**: Add the new study entry.
   - If **Yes**: Attempt to update missing fields in the existing entry.

2. **Dictionaries (Single Fields)**:
   - If "Median PFS" is `null` in the base repo but found in Chunk 15, update it.
   - If Chunk 15 says "5.5 months" and Chunk 16 says "5.5 months", keep the first one.

3. **Validation Logic**:
   - Prefer numerical strings (e.g., "25.6%") over descriptive ones.
   - Combine unique "Protocol IDs" into a single de-duplicated list.

---

## 5. Integrating Tables

Investigation Brochures are "Table-Heavy". Stage 3 handles 4 different types of table extraction:

1. **Pooled Groups**: Extracts how patients were categorized (Group 1, Group 2, etc.).
2. **Study Metadata**: Extracts Phase, Country, and Title for every unique Study ID found.
3. **Demographics**: Extracts Age, Gender, and Disease subtypes for each Group/Study.
4. **Detailed Safety**: Flattens large Adverse Event tables into row-based objects.

### Example Merged Result
```json
"baseline_demographics": [
  {
    "study_or_group_id": "Group 1",
    "n": 129,
    "median_age": "63.0",
    "female_percent": "46.5%"
  }
]
```

---

## Summary of Stage 3 Logic

1.  **Filter**: Only send "Safe" and "Efficacy" sections to save tokens.
2.  **Split**: Break into 4,000-char chunks with 500-char overlap.
3.  **Execute**: Run 37 parallel extraction tasks via GPT-4o + Pydantic.
4.  **Audit**: LLM reads each chunk against the specific schema rules.
5.  **Aggregate**: Merge fragmented JSON objects using the recursive merge algorithm.
6.  **Refine**: Final overwrite using **Azure Query Fields** for mission-critical numbers.

---

*Would you like to move on to **Stage 4: Validation & The Excel Generator**?*
