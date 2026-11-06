import json
import logging
import os
import threading
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile

from agent.pipeline import run_document_agent

logger = logging.getLogger(__name__)
app = FastAPI(title="Document Intelligence API")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DOCUMENT_TYPES = {
    "application/pdf": (b"%PDF-", ".pdf"),
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
}
document_states: dict[str, dict[str, object]] = {}
document_states_lock = threading.Lock()


def _update_document_state(document_id: str, **updates: object) -> None:
    with document_states_lock:
        state = document_states.setdefault(
            document_id,
            {"document_id": document_id, "status": "processing", "step": "queued"},
        )
        state.update(updates)


def process_document(document_id: str, document_path: Path) -> None:
    """Run the agent pipeline and persist its final result."""
    try:
        result = run_document_agent(
            document_id,
            document_path,
            lambda step: _update_document_state(document_id, step=step),
        )
        results_dir = Path(
            os.environ.get("DOCUMENT_RESULTS_DIR", document_path.parent.parent / "results")
        )
        results_dir.mkdir(parents=True, exist_ok=True)
        result_path = results_dir / f"{document_id}.json"
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _update_document_state(
            document_id,
            status="completed",
            step="completed",
            **{key: value for key, value in result.items() if key != "document_id"},
        )
    except Exception:
        logger.exception("Document processing failed for %s", document_id)
        _update_document_state(
            document_id,
            status="failed",
            step="failed",
            error="Document processing failed; see server logs.",
        )


@app.post("/documents", status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> dict[str, str]:
    file_type = DOCUMENT_TYPES.get(file.content_type or "")
    if file_type is None:
        raise HTTPException(
            status_code=415,
            detail="Only PDF, JPEG, and PNG documents are supported",
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 10 MB limit")

    signature, extension = file_type
    if not content.startswith(signature):
        raise HTTPException(status_code=400, detail="File content does not match its type")

    document_id = f"doc_{uuid4().hex}"
    storage_dir = Path(
        os.environ.get(
            "DOCUMENT_STORAGE_DIR",
            Path(__file__).resolve().parents[1] / "data" / "documents",
        )
    )
    storage_dir.mkdir(parents=True, exist_ok=True)
    document_path = storage_dir / f"{document_id}{extension}"
    document_path.write_bytes(content)

    with document_states_lock:
        document_states[document_id] = {
            "document_id": document_id,
            "status": "processing",
            "step": "queued",
        }
    background_tasks.add_task(process_document, document_id, document_path)
    return {"document_id": document_id, "status": "processing", "step": "queued"}


@app.get("/documents/{document_id}")
def get_document_status(document_id: str) -> dict[str, object]:
    with document_states_lock:
        state = document_states.get(document_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return state.copy()