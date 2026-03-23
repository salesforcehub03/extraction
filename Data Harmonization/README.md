# Data Harmonization System

A deterministic, rule-based system for converting biomedical data into a graph-based knowledge base for liver toxicity analysis.

## Project Structure

```
Data Harmonization/
├── src/                          # Source code
│   ├── config.py                 # Configuration and constants
│   ├── graph_schema.py           # Node, Edge, KnowledgeGraph classes
│   ├── biomarker_normalizer.py   # Biomarker name standardization
│   ├── data_loaders.py           # Standard data loaders
│   ├── data_loaders_optimized.py # Optimized loaders with chunking
│   ├── node_builder.py           # Standard node creation
│   ├── node_builder_optimized.py # Parallel node creation
│   ├── edge_builder.py           # Edge creation (all 4 types)
│   ├── graph_exporter.py         # JSON export
│   ├── azure_openai_helper.py    # Optional AI integration
│   ├── data_harmonization_system.py           # Standard orchestrator
│   ├── data_harmonization_system_optimized.py # Optimized orchestrator
│   └── .env                      # Configuration (create from .env.example)
├── Input files/                  # Input data sources
│   ├── belino_comprehensive_consolidated.xlsx
│   ├── preclinical_liver_summary 12.xlsx
│   ├── liver_chemistry_dataset_TOX14336.xlsx
│   └── dili_Clinical_output 2.csv
├── output/                       # Generated knowledge graphs
├── ui/                           # Streamlit UI (future)
├── requirements.txt              # Python dependencies
└── .env.example                  # Configuration template
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure (Optional)

```bash
# Copy template
copy .env.example src\.env

# Edit with your settings
notepad src\.env
```

### 3. Run Harmonization

**Standard Version:**
```bash
cd src
python data_harmonization_system.py
```

**Optimized Version (Recommended):**
```bash
cd src
python data_harmonization_system_optimized.py
```

## Features

### Graph Schema
- **13 Node Types**: Drug, Target, Pathway, Study, DoseGroup, Animal, Sample, Measurement, Analyte, AnimalStudy, ClinicalStudy, AdverseEvent, Biomarker
- **4 Edge Types**: tested_in, associated_with, observed_in, linked_to
- **Deterministic IDs**: SHA256-based for reproducibility

### Data Sources
- DrugBank: 4,304 drugs with unique IDs
- Belinostat: 60+ fields from 6 sheets
- Preclinical: 170 drugs with biomarkers
- TOX14336: Granular study structure
- Clinical DILI: 2,782 drugs

### Performance Optimizations
- **Parallel Processing**: 3-4x faster DrugBank mapping
- **Chunked Loading**: Memory-efficient for large files
- **Progress Tracking**: Real-time progress bars
- **Azure OpenAI**: Optional data validation & enrichment

## Output

- `output/knowledge_graph.json` - Complete graph
- `output/graph_statistics.json` - Statistics summary

## Documentation

- `implementation_plan.md` - Detailed technical plan
- `walkthrough.md` - Backend implementation guide
- `optimization_guide.md` - Performance enhancements

## Configuration Options

See `src/.env` for:
- Azure OpenAI settings
- Performance tuning (workers, chunk size)
- Feature flags (progress bars, validation)

## Next Steps

- [ ] Build Streamlit UI for visualization
- [ ] Add graph filtering and search
- [ ] Implement interactive node exploration

## License

Internal use only.
