# upload_temp.py
from fastapi import UploadFile, File, HTTPException, Body, APIRouter
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import datetime
import os, re, uuid, base64
from typing import Dict
from .config import TEMPLATE_DIR


# from REST_TEST.main import TEMPLATE_DIR
router = APIRouter(prefix="/templates", tags=["Templates"])

# ---------------------------
# Configuration / constants
# ---------------------------
# BASE_DIR = Path(__file__).resolve().parent
# TEMPLATES_DIR = BASE_DIR / "templates"
# OUTPUT_DIR = BASE_DIR / "outputs"
# TEMPLATES_DIR.mkdir(exist_ok=True)
# OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".docx", ".txt", ".j2", ".yaml", ".yml", ".json", ".cfg", ".ini", ".tmpl"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# ---------------------------
# Helper utilities
# ---------------------------
def secure_filename(filename: str) -> str:
    name = os.path.basename(filename or "")
    name = name.replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9_.-]", "", name)
    if not name:
        name = f"file_{uuid.uuid4().hex}"
    return name

def is_inside_directory(base_dir: Path, target_path: Path) -> bool:
    try:
        base_resolved = base_dir.resolve()
        target_resolved = target_path.resolve()
        return base_resolved == target_resolved or base_resolved in target_resolved.parents
    except Exception:
        return False

# ---------------------------
# Endpoints (attached to router!)
# ---------------------------

@router.post("/upload", summary="Upload template file (multipart/form-data)")
async def upload_template(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File extension '{ext}' is not allowed")

    safe_name = secure_filename(file.filename)
    dest = TEMPLATE_DIR / safe_name

    if not is_inside_directory(TEMPLATE_DIR, dest):
        raise HTTPException(status_code=400, detail="Invalid file path")

    size = 0
    try:
        with dest.open("wb") as out_file:
            while True:
                chunk = await file.read(1024 * 1024)  # 1 MB
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    out_file.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="File too large")
                out_file.write(chunk)
    finally:
        await file.close()

    return {"filename": safe_name, "size": size, "path": str(dest)}

@router.post("/upload-base64", summary="Upload template file as base64 JSON")
def upload_template_base64(payload: Dict = Body(...)):
    filename = payload.get("filename")
    content_b64 = payload.get("content")
    if not filename or not content_b64:
        raise HTTPException(status_code=400, detail="Missing filename or content")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extension '{ext}' not allowed")

    safe_name = secure_filename(filename)
    dest = TEMPLATE_DIR / safe_name

    import base64
    try:
        decoded = base64.b64decode(content_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}")

    if len(decoded) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    with dest.open("wb") as f:
        f.write(decoded)

    return {"filename": safe_name, "size": len(decoded), "path": str(dest)}

@router.get("/", summary="List available templates")
def list_templates():
    items = []
    for p in sorted(TEMPLATE_DIR.iterdir()):
        if p.is_file():
            stat = p.stat()
            items.append({
                "name": p.name,
                "size": stat.st_size,
                "modified": datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z"
            })
    return items

@router.get("/{filename}", summary="Download a template file")
def download_template(filename: str):
    safe_name = secure_filename(filename)
    dest = TEMPLATE_DIR / safe_name
    if not dest.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path=str(dest), filename=safe_name, media_type="application/octet-stream")

@router.delete("/{filename}", summary="Delete a template file")
def delete_template(filename: str):
    safe_name = secure_filename(filename)
    dest = TEMPLATE_DIR / safe_name
    if not dest.exists():
        raise HTTPException(status_code=404, detail="Not found")
    dest.unlink()
    return {"deleted": safe_name}
