from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter, Form
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import shutil
from .pdf2word import Pdf2WordConverter

pdf2word_app = APIRouter()
OUTPUT_DIR = Path("converted_files")
OUTPUT_DIR.mkdir(exist_ok=True)

converter = Pdf2WordConverter()  # optional: tesseract_cmd="/usr/bin/tesseract"

@pdf2word_app.post("/api/convert-file")
async def convert_file_api(
    file: UploadFile = File(...),
    conversion_type: str = Form(...),  # "pdf-word", "ocr-pdf-word", "image-word", "image-text"
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    ext = Path(file.filename).suffix.lower()
    pdf_exts = [".pdf"]
    image_exts = [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]

    # Save uploaded file temporarily
    input_path = OUTPUT_DIR / file.filename
    with input_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Decide output file name
    if conversion_type in ["image-text"]:
        output_path = OUTPUT_DIR / f"{input_path.stem}.txt"
    else:
        output_path = OUTPUT_DIR / f"{input_path.stem}.docx"

    # Run conversion
    try:
        if conversion_type == "pdf-word":
            res = converter.convert(str(input_path), str(output_path), mode="native")
        elif conversion_type == "ocr-pdf-word":
            res = converter.convert(str(input_path), str(output_path), mode="ocr")
        elif conversion_type == "image-word":
            res = converter.convert(str(input_path), str(output_path))
        elif conversion_type == "image-text":
            res = converter.convert(str(input_path), str(output_path))
        else:
            raise HTTPException(status_code=400, detail="Invalid conversion type")

        if not res["success"]:
            raise Exception(res.get("message", "Conversion failed"))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse({"download_url": f"/download/{output_path.name}"})

# Route to download converted files
@pdf2word_app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
        if filename.lower().endswith(".docx") else "text/plain"
    return FileResponse(file_path, media_type=media_type, filename=filename)
