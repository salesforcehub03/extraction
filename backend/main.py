import asyncio
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

# ── Path setup: make Data Extraction importable ───────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
EXTRACTION_DIR = BASE_DIR / "Data Extraction"
HARMONIZATION_DIR = BASE_DIR / "Data Harmonization"
UPLOAD_DIR = BASE_DIR / "backend" / "uploads"
OUTPUT_DIR = BASE_DIR / "backend" / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(EXTRACTION_DIR))

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(title="DILI Data Pipeline API (hcltech )", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global session store: session_id -> asyncio.Queue of SSE events ───────────
_SESSION_QUEUES: Dict[str, asyncio.Queue] = {}
_SESSION_RESULTS: Dict[str, Dict] = {}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse_event(event: str, data: Any) -> str:
    """Serialise a single SSE event frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _run_pipeline_task(session_id: str, pdf_path: str, output_dir: Path):
    """Background task: runs the pipeline in-process, pushing SSE events via a Queue."""
    queue: asyncio.Queue = _SESSION_QUEUES[session_id]

    async def on_step(step_id: str, status: str, message: str, progress: float):
        await queue.put(("step_update", {
            "step": step_id,
            "status": status,
            "message": message,
            "progress": progress,
        }))

    try:
        # Change working directory to Data Extraction so relative cache paths work
        original_cwd = os.getcwd()
        os.chdir(str(EXTRACTION_DIR))

        # Lazily import here so it runs in the right cwd
        from src.pipeline import DILIPipeline

        pipeline = DILIPipeline()
        output_json = str(output_dir / "extracted.json")

        metrics = await pipeline.process_document(
            file_path=pdf_path,
            output_path=output_json,
            on_step=on_step,
        )

        os.chdir(original_cwd)

        # Copy excel to the shared output dir with a stable name
        excel_src = metrics.get("excel_path")
        download_url = None
        excel_filename = None

        if excel_src and Path(excel_src).exists():
            excel_filename = f"extraction_{session_id}.xlsx"
            dest = OUTPUT_DIR / excel_filename
            shutil.copy(excel_src, dest)
            download_url = f"/api/download/{excel_filename}"

        # Push final metrics event
        await queue.put(("metrics", metrics))

        # Push complete event
        await queue.put(("complete", {
            "download_url": download_url,
            "excel_filename": excel_filename,
            "session_id": session_id,
        }))

        _SESSION_RESULTS[session_id] = {
            "status": "complete",
            "download_url": download_url,
            "metrics": metrics,
        }

    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print(f"[Pipeline Error] {exc}\n{tb}")
        try:
            os.chdir(original_cwd)
        except Exception:
            pass
        await queue.put(("pipeline_error", {
            "message": str(exc),
            "detail": (tb or "")[-500:],
        }))
        _SESSION_RESULTS[session_id] = {"status": "error", "error": str(exc)}
    finally:
        # Sentinel: tell the SSE stream to close
        await queue.put(("__done__", {}))


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/api/extract")
async def start_extraction(
    background_tasks: BackgroundTasks,
    ib_pdf: UploadFile = File(...),
):
    """
    Accepts the IB PDF, saves it, creates a session and starts the pipeline
    in the background. Returns a session_id so the client can open the SSE
    stream at GET /api/extract/stream/{session_id}.
    """
    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded PDF
    pdf_path = session_dir / ib_pdf.filename
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(ib_pdf.file, f)

    # Create the event queue for this session
    _SESSION_QUEUES[session_id] = asyncio.Queue()

    # Schedule pipeline as a background task
    background_tasks.add_task(
        _run_pipeline_task,
        session_id=session_id,
        pdf_path=str(pdf_path),
        output_dir=session_dir,
    )

    return {
        "session_id": session_id,
        "stream_url": f"/api/extract/stream/{session_id}",
        "filename": ib_pdf.filename,
    }


@app.get("/api/extract/stream/{session_id}")
async def stream_extraction(session_id: str):
    """
    SSE endpoint — streams pipeline step events to the browser.
    Events types: step_update | metrics | complete | pipeline_error
    """
    if session_id not in _SESSION_QUEUES:
        raise HTTPException(status_code=404, detail="Session not found")

    queue = _SESSION_QUEUES[session_id]

    async def event_generator():
        # Send an initial ping so the browser confirms the connection
        yield _sse_event("ping", {"session_id": session_id})
        try:
            while True:
                event_type, data = await asyncio.wait_for(queue.get(), timeout=600)
                if event_type == "__done__":
                    break
                yield _sse_event(event_type, data)
        except asyncio.TimeoutError:
            yield _sse_event("pipeline_error", {"message": "Pipeline timed out after 10 minutes."})
        finally:
            # Clean up queue (keep results for possible re-poll)
            _SESSION_QUEUES.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/extract/status/{session_id}")
async def get_status(session_id: str):
    """Poll endpoint for clients that can't use SSE."""
    result = _SESSION_RESULTS.get(session_id)
    if result is None:
        return {"status": "running"}
    return result


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── Harmonization endpoint (unchanged, kept for compatibility) ────────────────

@app.post("/api/harmonize")
async def harmonize_data(
    ib_excel: UploadFile = File(...),
    clinical_excel: Optional[UploadFile] = File(None),
    preclinical_excel: Optional[UploadFile] = File(None),
    meta_file: Optional[UploadFile] = File(None),
    sig_file: Optional[UploadFile] = File(None),
):
    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    excel_path = session_dir / ib_excel.filename
    with open(excel_path, "wb") as f:
        shutil.copyfileobj(ib_excel.file, f)

    other_file_paths = []
    for upload, prefix in [
        (clinical_excel, "Clinical_"),
        (preclinical_excel, "Preclinical_"),
    ]:
        if upload:
            dest = session_dir / f"{prefix}{upload.filename}"
            with open(dest, "wb") as f:
                shutil.copyfileobj(upload.file, f)
            other_file_paths.append(dest)

    meta_path = sig_path = None
    for upload, attr in [(meta_file, "meta_path"), (sig_file, "sig_path")]:
        if upload:
            dest = session_dir / upload.filename
            with open(dest, "wb") as f:
                shutil.copyfileobj(upload.file, f)
            if attr == "meta_path":
                meta_path = dest
            else:
                sig_path = dest

    try:
        sys.path.insert(0, str(BASE_DIR / "backend"))
        from utils.merge import merge_files
        consolidated = merge_files(
            excel_path, other_file_paths,
            output_path=session_dir / "consolidated.xlsx",
        )

        kg_output = session_dir / "knowledge_graph.json"
        sys.path.insert(0, str(HARMONIZATION_DIR))

        import subprocess
        cmd = [
            sys.executable,
            str(HARMONIZATION_DIR / "src" / "unified_kg_builder.py"),
            "--build", "--validate",
            "--input_file", str(consolidated),
            "--output_file", str(kg_output),
        ]
        if meta_path:
            cmd += ["--meta_file", str(meta_path)]
        if sig_path:
            cmd += ["--sig_file", str(sig_path)]

        result = subprocess.run(cmd, cwd=str(HARMONIZATION_DIR), capture_output=True, text=True)
        if result.returncode != 0:
            error_detail = (result.stderr or "")[-1000:]
            raise RuntimeError(error_detail)

        final_filename = f"knowledge_graph_{session_id}.json"
        shutil.copy(kg_output, OUTPUT_DIR / final_filename)
        return {"session_id": session_id, "download_url": f"/api/download/{final_filename}"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8124)
