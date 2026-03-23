import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional

@dataclass
class ChunkTelemetry:
    chunk_index: int
    section_type: str
    latency_seconds: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    error: Optional[str] = None

class TelemetryTracker:
    """Tracks performance, costs, and traceability across the pipeline."""
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.start_time = time.time()
        self.chunks: List[ChunkTelemetry] = []
        self.metadata: Dict[str, Any] = {
            "version": "v1.0",
            "model_name": "azure-gpt-4o",
            "total_latency": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
        }

    def start_chunk(self) -> float:
        """Returns the start time for a chunk extraction."""
        return time.time()

    def end_chunk(self, chunk_index: int, section_type: str, start_time: float, 
                  tokens: Dict[str, int], retry_count: int = 0, error: str = None):
        """Records telemetry for a single chunk."""
        latency = time.time() - start_time
        prompt_t = tokens.get("prompt_tokens", 0)
        completion_t = tokens.get("completion_tokens", 0)
        total_t = tokens.get("total_tokens", 0)
        
        telemetry = ChunkTelemetry(
            chunk_index=chunk_index,
            section_type=section_type,
            latency_seconds=round(latency, 3),
            prompt_tokens=prompt_t,
            completion_tokens=completion_t,
            total_tokens=total_t,
            retry_count=retry_count,
            error=error
        )
        self.chunks.append(telemetry)
        
        # Accumulate totals
        self.metadata["total_prompt_tokens"] += prompt_t
        self.metadata["total_completion_tokens"] += completion_t
        self.metadata["total_tokens"] += total_t

    def save_report(self, run_id: str = "latest"):
        """Saves the final telemetry report to JSON."""
        duration = time.time() - self.start_time
        self.metadata["total_latency"] = round(duration, 3)
        self.metadata["run_id"] = run_id
        self.metadata["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        report = {
            "metadata": self.metadata,
            "chunks": [asdict(c) for c in self.chunks]
        }
        
        report_path = self.output_dir / f"telemetry_{run_id}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n[Telemetry] Report saved to {report_path}")
        print(f"  Total Duration: {self.metadata['total_latency']}s")
        print(f"  Total Tokens: {self.metadata['total_tokens']}")

    def get_summary(self) -> str:
        """Returns a human-readable summary of the run performance."""
        m = self.metadata
        return (f"Run Summary ({m.get('run_id', 'unknown')}):\n"
                f"- Duration: {m['total_latency']}s\n"
                f"- Prompt Tokens: {m['total_prompt_tokens']}\n"
                f"- Completion Tokens: {m['total_completion_tokens']}\n"
                f"- Total Tokens: {m['total_tokens']}")
