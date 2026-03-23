import asyncio
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from src.pipeline import DILIPipeline

async def main():
    # Use the existing belino-ib.pdf
    pdf_path = "belino-ib.pdf"
    
    # Initialize pipeline
    # We want to see metrics, so on_step will just print progress
    def on_step(step_id, status, message, progress):
        print(f"[{progress}%] {step_id}: {status} - {message}")
    
    pipeline = DILIPipeline()
    
    print(f"Starting pipeline on {pdf_path}...")
    final_data, final_metrics = await pipeline.process_document(pdf_path, on_step=on_step)
    
    print("\n" + "="*50)
    print("FINAL METRICS (Sent to UI):")
    print(json.dumps(final_metrics, indent=2))
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
