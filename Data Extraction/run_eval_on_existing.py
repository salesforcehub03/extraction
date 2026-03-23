import asyncio
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from src.evaluator import ExtractionEvaluator

async def main():
    # Use existing files for quick verification
    gt_path = "ground_truth.json"
    if not os.path.exists(gt_path):
        gt_path = None
        print("[Info] No ground_truth.json found. Running in REFERENCE-FREE mode.")
    else:
        print(f"[Info] Found {gt_path}. Running in GROUND-TRUTH mode.")

    out_path = "output.json"
    ctx_path = "cache_classified.json"
    
    print(f"Running evaluator on {out_path}...")
    evaluator = ExtractionEvaluator(
        ground_truth_path=gt_path,
        use_llm=True,
        context_path=ctx_path
    )
    
    results = await evaluator.evaluate(out_path)
    evaluator.print_report(results)

if __name__ == "__main__":
    asyncio.run(main())
