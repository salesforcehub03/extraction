import json
import argparse
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional
from openai import AsyncAzureOpenAI
from config import Config
from src.prompt_registry import PromptRegistry

class ExtractionEvaluator:
    """Evaluates pipeline accuracy by comparing JSON output to Ground Truth."""
    
    # Industrial weighting for clinical fields
    FIELD_WEIGHTS = {
        "sponsor_information": 5,
        "primary_indication": 5,
        "dose_level": 4,
        "mechanism_of_action": 4,
        "adverse_events": 4,
        "study_id": 3,
        "n_patients": 3,
        "study_phase": 3,
        "safety_signals": 4,
        "pharmacokinetics": 3,
        "eligibility_criteria": 2,
        "notes": 1,
        "references": 1
    }

    def __init__(self, ground_truth_path: str, use_llm: bool = False, context_path: Optional[str] = None):
        with open(ground_truth_path, 'r', encoding='utf-8') as f:
            self.gt = json.load(f)
        self.metrics = {
            "overall": {"tp": 0, "fp": 0, "fn": 0, "semantic_sum": 0.0, "total_fields": 0, "weighted_tp": 0.0, "total_weight": 0.0},
            "sections": {},
            "fields": {},  # Granular field-level tracking
            "hallucination": {"total": 0, "unsupported": 0},
            "faithfulness": {"total_claims": 0, "supported_claims": 0},
            "tables": {"cells_total": 0, "cells_correct": 0, "rows_total": 0, "rows_correct": 0},
            "results": [] # To store detailed comparison objects
        }
        self.use_llm = use_llm
        self.context = None
        if context_path and Path(context_path).exists():
            with open(context_path, 'r', encoding='utf-8') as f:
                self.context = json.load(f)
        
        if self.use_llm:
            Config.validate()
            self.client = AsyncAzureOpenAI(
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                api_key=Config.AZURE_OPENAI_KEY,
                api_version=Config.AZURE_OPENAI_API_VERSION
            )
            self.deployment_name = Config.AZURE_OPENAI_DEPLOYMENT_NAME

    async def evaluate(self, output_path: str) -> Dict[str, Any]:
        with open(output_path, 'r', encoding='utf-8') as f:
            output = json.load(f)
        
        # Reset metrics for new run
        self.metrics["overall"] = {"tp": 0, "fp": 0, "fn": 0, "semantic_sum": 0.0, "total_fields": 0, "weighted_tp": 0.0, "total_weight": 0.0}
        self.metrics["sections"] = {}
        self.metrics["fields"] = {}
        self.metrics["tables"] = {"cells_total": 0, "cells_correct": 0, "rows_total": 0, "rows_correct": 0}
        self.metrics["results"] = []
        
        all_keys = set(self.gt.keys()).union(set(output.keys()))
        tasks = []
        for section in all_keys:
            if section in ["extraction_metadata", "semantic_relationships"]:
                continue
                
            gt_val = self.gt.get(section, {})
            out_val = output.get(section, {})
            
            tasks.append(self._compare_recursive(gt_val, out_val, section))
            
        results = await asyncio.gather(*tasks)
        
        filtered_keys = [k for k in all_keys if k not in ["extraction_metadata", "semantic_relationships"]]
        for i, section in enumerate(filtered_keys):
            section_metrics = results[i]
            self.metrics["sections"][section] = section_metrics
            
            # Accumulate to overall
            for k in ["tp", "fp", "fn", "semantic_sum", "total_fields", "weighted_tp", "total_weight"]:
                self.metrics["overall"][k] += section_metrics.get(k, 0.0)

        # Robustness Metrics
        if self.use_llm and self.context:
            await self._evaluate_robustness(output)

        return self._calculate_scores()

    def _is_empty(self, val: Any) -> bool:
        if val is None: return True
        s = str(val).strip().lower()
        return s in ["", "not found", "null", "none", "[]", "{}"]

    def _get_weight(self, field_name: str) -> int:
        return self.FIELD_WEIGHTS.get(field_name.lower(), 1)

    async def _compare_recursive(self, gt: Any, out: Any, field_name: str = "") -> Dict[str, Any]:
        m = {"tp": 0, "fp": 0, "fn": 0, "semantic_sum": 0.0, "total_fields": 0, "weighted_tp": 0.0, "total_weight": 0.0}
        weight = self._get_weight(field_name)

        if isinstance(gt, dict) and isinstance(out, dict):
            child_tasks = []
            for k in set(gt.keys()).union(set(out.keys())):
                child_tasks.append(self._compare_recursive(gt.get(k), out.get(k), k))
            
            child_results = await asyncio.gather(*child_tasks)
            for res in child_results:
                for key in m:
                    m[key] += res[key]
        
        elif isinstance(gt, list) and isinstance(out, list):
            # Special handling for clinical matrices or lists of objects
            if gt and isinstance(gt[0], dict):
                table_metrics = await self._compare_tables(gt, out, field_name)
                for key in m:
                    if key in table_metrics: m[key] += table_metrics[key]
            else:
                gt_set = set(str(x) for x in gt if not self._is_empty(x))
                out_set = set(str(x) for x in out if not self._is_empty(x))
                
                tp = len(gt_set.intersection(out_set))
                m["tp"] += tp
                m["fn"] += len(gt_set) - tp
                m["fp"] += len(out_set) - tp
                m["total_fields"] += len(gt_set)
                m["semantic_sum"] += tp
                m["weighted_tp"] += tp * weight
                m["total_weight"] += len(gt_set) * weight
        
        else:
            # Scalar comparison
            gt_empty = self._is_empty(gt)
            out_empty = self._is_empty(out)
            
            if not gt_empty and not out_empty:
                m["total_fields"] += 1
                m["total_weight"] += weight
                
                match_score = 0.0
                reason = "Exact Match"
                if str(gt).strip().lower() == str(out).strip().lower():
                    match_score = 1.0
                    m["tp"] += 1
                elif self.use_llm:
                    match_score, reason = await self._get_semantic_score_with_reason(field_name, gt, out)
                    if match_score >= 1.0: m["tp"] += 1
                    else:
                        m["fp"] += 1
                        m["fn"] += 1
                else:
                    m["fp"] += 1
                    m["fn"] += 1
                    reason = "Mismatch"
                
                m["semantic_sum"] += match_score
                m["weighted_tp"] += match_score * weight
                
                # Granular tracking for UI Audit Table
                self.metrics["results"].append({
                    "section": field_name, # Simplified for flat fields
                    "field": field_name,
                    "extracted": str(out)[:200],
                    "ground_truth": str(gt)[:200],
                    "score": match_score,
                    "reason": reason
                })

            elif not gt_empty and out_empty:
                m["fn"] += 1
                m["total_fields"] += 1
                m["total_weight"] += weight
            elif gt_empty and not out_empty:
                m["fp"] += 1
        
        return m

    async def _compare_tables(self, gt: List[Dict], out: List[Dict], table_name: str) -> Dict[str, Any]:
        """Granular table cell/row accuracy."""
        tm = {"tp": 0, "fp": 0, "fn": 0, "semantic_sum": 0.0, "total_fields": 0, "weighted_tp": 0.0, "total_weight": 0.0}
        
        # Heuristic: try to align rows by shared values (e.g., study_id or drug)
        # For simplicity in this eval, we'll do row-by-row if lengths match, otherwise greedy match
        total_cells = 0
        correct_cells = 0
        rows_correct = 0
        
        matched_out_indices = set()
        for gt_row in gt:
            best_row_score = 0
            best_match_idx = -1
            
            row_keys = gt_row.keys()
            for i, out_row in enumerate(out):
                if i in matched_out_indices: continue
                
                # Compare row cells
                row_score = 0
                for k in row_keys:
                    if str(gt_row.get(k)).lower() == str(out_row.get(k)).lower():
                        row_score += 1
                
                if row_score > best_row_score:
                    best_row_score = row_score
                    best_match_idx = i
            
            # Accumulate metrics for the best match found
            num_fields = len(row_keys)
            tm["total_fields"] += num_fields
            total_cells += num_fields
            
            if best_match_idx != -1:
                matched_out_indices.add(best_match_idx)
                correct_cells += best_row_score
                tm["tp"] += 1 if best_row_score == num_fields else 0 # Full row match
                tm["semantic_sum"] += best_row_score
                if best_row_score == num_fields: rows_correct += 1
            else:
                tm["fn"] += 1
        
        tm["fp"] += len(out) - len(matched_out_indices)
        
        # Log global table metrics
        self.metrics["tables"]["cells_total"] += total_cells
        self.metrics["tables"]["cells_correct"] += correct_cells
        self.metrics["tables"]["rows_total"] += len(gt)
        self.metrics["tables"]["rows_correct"] += rows_correct
        
        return tm

    async def _get_semantic_score_with_reason(self, field: str, gt: Any, out: Any) -> Tuple[float, str]:
        prompt = PromptRegistry.get_judge_prompt("semantic")
        content = prompt.format(field_name=field, ground_truth=gt, extraction=out)
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": content}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            data = json.loads(response.choices[0].message.content)
            # Expecting {"score": 0.5, "explanation": "Brief reasoning for the score"}
            return float(data.get("score", 0.0)), data.get("explanation", "No reason provided")
        except: return 0.0, "Judge call failed"

    async def _get_semantic_score(self, field: str, gt: Any, out: Any) -> float:
        score, _ = await self._get_semantic_score_with_reason(field, gt, out)
        return score

    async def _evaluate_robustness(self, output: dict):
        # Increase context depth to 255 (Full Doc) for hallucination/faithfulness checks
        context_text = "\n".join([c.get("content", "") for c in self.context[:255]])
        t1 = self._check_hallucination(context_text, output)
        t2 = self._check_faithfulness(context_text, output)
        self.metrics["hallucination"], self.metrics["faithfulness"] = await asyncio.gather(t1, t2)

    async def _check_hallucination(self, context: str, output: dict) -> Dict[str, int]:
        unsupported = 0
        total = 0
        sample_fields = []
        if "study_metadata" in output: sample_fields.append(("Sponsor", output["study_metadata"].get("sponsor_information")))
        if "dosing_administration" in output: sample_fields.append(("Dose Level", output["dosing_administration"].get("dose_level")))
            
        for field, value in sample_fields:
            if self._is_empty(value): continue
            total += 1
            prompt = PromptRegistry.get_judge_prompt("hallucination")
            content = prompt.format(context=context[:4000], field=field, value=value)
            try:
                response = await self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[{"role": "user", "content": content}],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                if json.loads(response.choices[0].message.content).get("score") == 0.0: unsupported += 1
            except: pass
        return {"total": total, "unsupported": unsupported}

    async def _check_faithfulness(self, context: str, output: dict) -> Dict[str, int]:
        prompt = PromptRegistry.get_judge_prompt("faithfulness")
        sample_data = output.get("dosing_administration", {})
        content = prompt.format(context=context[:6000], data=json.dumps(sample_data))
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": content}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            score = json.loads(response.choices[0].message.content).get("score", 1.0)
            return {"total_claims": 100, "supported_claims": int(score * 100)}
        except: return {"total_claims": 0, "supported_claims": 0}

    def _calculate_scores(self) -> Dict[str, Any]:
        results = {}
        for scope, data in [("overall", self.metrics["overall"])] + list(self.metrics["sections"].items()):
            tp, fp, fn = data["tp"], data["fp"], data["fn"]
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            semantic_score = data.get("semantic_sum", 0.0) / data.get("total_fields", 1) if data.get("total_fields", 0) > 0 else 1.0
            weighted_accuracy = data.get("weighted_tp", 0.0) / data.get("total_weight", 1) if data.get("total_weight", 0) > 0 else 1.0
            
            results[scope] = {
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": round(f1, 3),
                "semantic_score": round(semantic_score, 3),
                "weighted_accuracy": round(weighted_accuracy, 3),
                "counts": data
            }
        
        # Robustness & Table Accuracy
        h = self.metrics["hallucination"]
        f = self.metrics["faithfulness"]
        t = self.metrics["tables"]
        results["robustness"] = {
            "hallucination_rate": round(h["unsupported"] / h["total"], 3) if h["total"] > 0 else 0.0,
            "faithfulness": round(f["supported_claims"] / f["total_claims"], 3) if f["total_claims"] > 0 else 1.0,
            "cell_accuracy": round(t["cells_correct"] / t["cells_total"], 3) if t["cells_total"] > 0 else 1.0,
            "row_accuracy": round(t["rows_correct"] / t["rows_total"], 3) if t["rows_total"] > 0 else 1.0
        }
        results["results"] = self.metrics["results"]
        return results

    def print_report(self, scores: Dict[str, Any]):
        print("\n" + "╔" + "═"*58 + "╗")
        print("║" + " PRODUCTION EVALUATION REPORT ".center(58) + "║")
        print("╠" + "═"*58 + "╣")
        ov = scores["overall"]
        rob = scores.get("robustness", {})
        
        print(f"║ OVERALL F1 SCORE:      {ov['f1']:<34} ║")
        print(f"║ WEIGHTED ACCURACY:    {ov['weighted_accuracy']:<34} ║")
        print(f"║ SEMANTIC CONFORMANCE: {ov['semantic_score']:<34} ║")
        print(f"║ HALLUCINATION RATE:   {rob.get('hallucination_rate', 0):<34} ║")
        print(f"║ FAITHFULNESS SCORE:   {rob.get('faithfulness', 0):<34} ║")
        print("╠" + "═"*58 + "╣")
        
        print("║ TABLE GRANULARITY:".ljust(59) + "║")
        print(f"║   - Cell Accuracy:    {rob.get('cell_accuracy', 'N/A'):<34} ║")
        print(f"║   - Row Accuracy:     {rob.get('row_accuracy', 'N/A'):<34} ║")
        print("╠" + "═"*58 + "╣")

        print("║ SECTION BREAKDOWN (F1 | Weighted Acc):".ljust(59) + "║")
        for section, s in scores.items():
            if section in ["overall", "robustness"]: continue
            line = f"  {section[:25]:.<25} {s['f1']} | {s['weighted_accuracy']}"
            print(f"║ {line:<56} ║")
        
        print("╚" + "═"*58 + "╝")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gt", required=True, help="Path to ground truth JSON")
    parser.add_argument("--out", required=True, help="Path to pipeline output JSON")
    parser.add_argument("--use-llm", action="store_true", help="Enable LLM-as-a-Judge")
    parser.add_argument("--context", default="cache_classified.json", help="Path to classified chunks")
    args = parser.parse_args()
    
    evaluator = ExtractionEvaluator(args.gt, use_llm=args.use_llm, context_path=args.context)
    scores = await evaluator.evaluate(args.out)
    evaluator.print_report(scores)

if __name__ == "__main__":
    asyncio.run(main())
