import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_step(step_name, command, cwd):
    print(f"\n{'='*60}")
    print(f"STEP: {step_name}")
    print(f"Command: {command}")
    print(f"Directory: {cwd}")
    print(f"{'='*60}\n")
    
    try:
        # Run the command
        # using sys.executable ensures we use the same python interpreter
        full_cmd = f'"{sys.executable}" {command}'
        result = subprocess.run(full_cmd, shell=True, cwd=cwd, check=True, text=True)
        print(f"\n[SUCCESS] {step_name} completed.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] {step_name} failed with exit code {e.returncode}")
        return False

def main():
    parser = argparse.ArgumentParser(description="End-to-End Data Harmonization Pipeline")
    parser.add_argument("--input_pdf", "-i", required=True, help="Path to input Investigator Brochure PDF")
    parser.add_argument("--drug_name", "-d", default="Belinostat", help="Name of the drug (for tagging)")
    parser.add_argument("--output_dir", "-o", default=r"D:\AViiD\FullPipelineOutput", help="Directory for all outputs")
    
    args = parser.parse_args()
    
    # Setup Paths
    base_dir = Path(r"D:\AViiD")
    extraction_dir = base_dir / "Data Extraction"
    harmonization_dir = base_dir / "Data Harmonization"
    output_dir = Path(args.output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    input_pdf = Path(args.input_pdf).resolve()
    if not input_pdf.exists():
        print(f"Error: PDF not found at {input_pdf}")
        sys.exit(1)

    # 1. Define Output Paths
    json_output = output_dir / f"{args.drug_name}_extracted.json"
    excel_output = output_dir / f"{args.drug_name}_extracted_complete.xlsx"
    kg_output = output_dir / f"{args.drug_name}_knowledge_graph.json"

    # --- STEP 1: EXTRACTION ---
    # python src/pipeline.py --input "..." --output "..."
    if not run_step(
        "Data Extraction", 
        f'src/pipeline.py --input "{input_pdf}" --output "{json_output}"', 
        cwd=extraction_dir
    ):
        sys.exit(1)

    # --- STEP 2: EXCEL GENERATION ---
    # python src/comprehensive_excel_writer.py "..."
    # Note: Excel writer auto-appends '_complete.xlsx' to the input filename stem
    # We need to predict the output name to pass to the next step
    # json_output is ".../Drug_extracted.json" -> Excel will be ".../Drug_extracted_complete.xlsx"
    
    if not run_step(
        "Excel Generation",
        f'src/comprehensive_excel_writer.py "{json_output}"',
        cwd=extraction_dir
    ):
        sys.exit(1)

    # --- STEP 3: HARMONIZATION ---
    # python src/unified_kg_builder.py --build --validate --input_file "..." --output_file "..."
    
    if not run_step(
        "Data Harmonization",
        f'src/unified_kg_builder.py --build --validate --input_file "{excel_output}" --output_file "{kg_output}"',
        cwd=harmonization_dir
    ):
        sys.exit(1)

    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"Final Knowledge Graph: {kg_output}") # Note: KG builder currently writes to hardcoded output, we might want to check where it went
    print("Check 'Data Harmonization/belino_refined_kb.json' (default output) or configure builder to accept output path.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
