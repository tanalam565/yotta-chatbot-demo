# src/api/routes.py
from fastapi import APIRouter, HTTPException, Request, FastAPI, Form
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel
from src.chatbot.rag_engine import RAGEngine
from fastapi import UploadFile, File
from typing import List
import os
import shutil

router = APIRouter(prefix="/api", tags=["chat"])
_engine = RAGEngine()

def register_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid request body", "errors": exc.errors()},
        )

class ChatRequest(BaseModel):
    message: Optional[str] = None
    session_id: Optional[str] = None

@router.post("/chat")
async def chat(req: Request):
    try:
        data = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body must be JSON")

    print("DEBUG /api/chat payload:", data)

    message = (data.get("message") or data.get("question") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Field 'message' is required")

    session_id = data.get("session_id") or str(uuid4())

    result = _engine.qa_with_history(session_id, message)
    return result

ALLOWED_EXTS = {".txt", ".md", ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}

@router.post("/upload")
async def upload(files: List[UploadFile] = File(...), session_id: str = Form(...)):
    """
    Accept files and ADD to session-specific directory.
    Files accumulate - previous uploads are NOT deleted.
    """
    saved = []
    rejected = []
    
    # Create session directory if it doesn't exist
    session_dir = os.path.join("data", "uploads", session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    print(f"[upload] Session directory: {session_dir}")
    print(f"[upload] Files before upload: {os.listdir(session_dir) if os.path.exists(session_dir) else []}")

    for f in files:
        name = os.path.basename(f.filename or "")
        ext = os.path.splitext(name)[1].lower()
        if ext not in ALLOWED_EXTS:
            rejected.append(name or "unnamed")
            continue
        
        # Create unique filename if file already exists
        safe = name.replace("/", "_").replace("\\", "_")
        path = os.path.join(session_dir, safe)
        
        # If file exists, add a number to make it unique
        counter = 1
        while os.path.exists(path):
            name_part, ext_part = os.path.splitext(safe)
            path = os.path.join(session_dir, f"{name_part}_{counter}{ext_part}")
            counter += 1
        
        content = await f.read()
        with open(path, "wb") as out:
            out.write(content)
        saved.append(os.path.basename(path))
    
    print(f"[upload] Files after upload: {os.listdir(session_dir)}")

    # Rebuild session index with ALL files in the directory
    _engine.build_session_index(session_id, session_dir)

    return {"saved": saved, "rejected": rejected, "count": len(saved)}

@router.post("/clear-session")
async def clear_session(session_id: str = Form(...)):
    """
    Clear uploaded files and session index for a given session.
    """
    print(f"[clear-session] Clearing session: {session_id}")
    
    # Delete uploaded files
    session_dir = os.path.join("data", "uploads", session_id)
    if os.path.exists(session_dir):
        print(f"[clear-session] Deleting directory: {session_dir}")
        shutil.rmtree(session_dir)
    
    # Clear session index from memory
    _engine.clear_session_index(session_id)
    
    # Clear chat history
    from src.chatbot.rag_engine import _SESSION_MEMORY
    if session_id in _SESSION_MEMORY:
        del _SESSION_MEMORY[session_id]
    
    return {"message": "Session cleared successfully"}