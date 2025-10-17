import datetime
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pandas as pd
import uuid
from collections import Counter
import time
import yt_dlp
from fastapi import BackgroundTasks, Body
from io import BytesIO

from utils.scrap import get_all_products
from utils.YTD import DOWNLOAD_DIR, get_available_formats, sanitize_url
from utils import pdf2wordRouterApi
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.responses import FileResponse, JSONResponse,HTMLResponse
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict
import os
import logging
from io import BytesIO
from fastapi.responses import JSONResponse
from docx import Document
from utils.doc_generator import extract_placeholders, generate_hld_doc, _replace_placeholders_in_paragraph
from utils.upload_temp import router as templates_router
from utils.accesstovm import ssh_connect,test_connection
from utils.config import TEMPLATE_DIR, OUTPUT_DIR
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import mysql.connector
from utils.DB import DB_ACTIONS as DA





# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app = FastAPI(title="Dynamic HLD Generator")
app.include_router(templates_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")
app.include_router(DA)
p2w=pdf2wordRouterApi.pdf2word_app
app.include_router(p2w)

timestamp_format=datetime.datetime.now().strftime("%Y%m%d_%I-%M-%S%p")




@app.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    templates_list = [t for t in os.listdir(TEMPLATE_DIR) if t.endswith((".docx", ".txt"))]
    files_list = [f for f in os.listdir(OUTPUT_DIR) if f.endswith((".docx", ".txt"))]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "templates": templates_list,
        "files": files_list
    })
# Request model
class GenerateRequest(BaseModel):
    template: str = Field(..., example="hldaa_template.docx")
    fields: Dict[str, str] = Field(
        ...,
        example={
            "project_name": "MyApp",
            "author_name": "Pramod",
            "date": "2025-09-23"
        }
    )


@app.get("/template-schema", summary="Get template placeholders in ready-to-fill format")
def get_template_schema(template: str = Query(..., example="hld_template.docx")):
    """
    Return template placeholders as a dictionary ready for filling values.
    Example output:
    {
        "template": "hld_template.docx",
        "fields": {
            "system_type": "",
            "author_name": "",
            "date": "",
            "project_name": ""
        }
    }
    """
    template_path = os.path.join(TEMPLATE_DIR, template)
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template '{template}' not found")

    try:
        fields = extract_placeholders(template_path)
        field_dict = {field: "" for field in fields}  # keys with empty values
        return {"template": template, "fields": field_dict}
    except Exception as e:
        logging.exception(f"Error extracting schema from template '{template}'")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/generate", summary="Generate HLD document")
def generate_document(payload: GenerateRequest):
    """
    Accept dynamic field values and generate the final HLD document.
    """
    template_path = os.path.join(TEMPLATE_DIR, payload.template)
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template '{payload.template}' not found")

    try:
        expected_fields = extract_placeholders(template_path)
        missing_fields = [f for f in expected_fields if f not in payload.fields]

        if missing_fields:
            raise HTTPException(status_code=400, detail=f"Missing fields: {missing_fields}")

        filename = generate_hld_doc(template_path, payload.fields, output_dir=OUTPUT_DIR)
        download_url = f"/download/{filename}"
        return {"message": "Document generated successfully", "download_url": download_url}

    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"Error generating document from template '{payload.template}'")
        raise HTTPException(status_code=500, detail=str(e))
################################################################################

################################################################################

@app.post("/preview", summary="Preview HLD document content without saving")
def preview_document(payload: GenerateRequest):
    """
    Fill the template with given fields and return the text content for preview.
    """
    template_path = os.path.join(TEMPLATE_DIR, payload.template)
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template '{payload.template}' not found")

    try:
        expected_fields = extract_placeholders(template_path)
        missing_fields = [f for f in expected_fields if f not in payload.fields]

        if missing_fields:
            raise HTTPException(status_code=400, detail=f"Missing fields: {missing_fields}")

        doc = Document(template_path)

        # Replace placeholders in doc in memory
        for para in doc.paragraphs:
            _replace_placeholders_in_paragraph(para, payload.fields)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    _replace_placeholders_in_paragraph(cell, payload.fields)

        # Combine all text for preview
        full_text = "\n".join([p.text for p in doc.paragraphs])
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    full_text += "\n" + cell.text

        return JSONResponse({"preview_text": full_text})

    except Exception as e:
        logging.exception(f"Error generating preview for template '{payload.template}'")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/download_doc/{filename}")
def download_document(filename: str):
    print("Downloading file:", filename)
    file_path = os.path.join(OUTPUT_DIR, filename)
    print("Full file path:", file_path)
    print("Files in OUTPUT_DIR:", os.listdir(OUTPUT_DIR))
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(file_path, filename=filename)


@app.get("/list-generated-files")
def list_generated_files():
    return {"output_dir": str(OUTPUT_DIR), "files": os.listdir(OUTPUT_DIR)}



#
@app.post("/router-config", summary="Send router configuration")
def router_config(payload: dict):
    commands = payload.get("commands")
    if not commands:
        raise HTTPException(status_code=400, detail="No commands provided")

    # Here you can intepip grate logic to send commands to router via SSH, Netmiko, etc.
    # For example, we'll just echo back the commands for now
    result = f"Commands received:\n{commands}"
    return {"result": result}

@app.get("/txt-schema")
def txt_schema(template: str):
    template_path = os.path.join(TEMPLATE_DIR, template)
    if not os.path.exists(template_path):
        raise HTTPException(404, f"Template '{template}' not found")

    # For TXT, we detect placeholders as {{key}}
    fields = {}
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
        import re
        matches = re.findall(r"\{\{(\w+)\}\}", content)
        for m in matches:
            fields[m] = ""
    return {"template": template, "fields": fields}


@app.post("/generate-txt")
def generate_txt(payload: GenerateRequest):
    template_path = os.path.join(TEMPLATE_DIR, payload.template)
    output_file = os.path.join(OUTPUT_DIR, f"{timestamp_format}_{payload.template}")

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
        for key, val in payload.fields.items():
            content = content.replace(f"{{{{{key}}}}}", val)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    download_url = f"/download/{os.path.basename(output_file)}"
    return {"message": "TXT document generated", "download_url": download_url}


@app.post("/preview-txt")
def preview_txt(payload: GenerateRequest):
    template_path = os.path.join(TEMPLATE_DIR, payload.template)
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
        for key, val in payload.fields.items():
            content = content.replace(f"{{{{{key}}}}}", val)
    return {"preview_text": content}
######################
#########################
###############
# ------------------------------
# Fetch products from DB
# ------------------------------
@app.get("/scrap/flipkart")
def flipkart_scrap(url: str):
    try:
        from utils.scrap import scrape_flipkart
        result = scrape_flipkart(url, max_pages=1)
        return {"count": result['count'], "data": get_all_products()}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------
# Download CSV from outputs
# ------------------------------
@app.get("/scrap/download")
def download_flipkart():
    path = "outputs/flipkart_all_pages.csv"
    if os.path.exists(path):
        return FileResponse(path, media_type="text/csv", filename="flipkart_results.csv")
    return JSONResponse({"error": "File not found"}, status_code=404)
    ##############YTD
progress = {"download": 0, "convert": 0, "file": ""}

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/youtube/formats")
def get_formats(url: str = Query(...)):
    try:
        print("Scrapping Links for Format")
        clean_url = sanitize_url(url)
        formats = get_available_formats(clean_url)
        if not formats:
            return {"error": "No downloadable formats found for this video."}
        return {"formats": formats}
    except Exception as e:
        return {"error": f"Failed to fetch formats: {str(e)}"}

@app.post("/youtube/start")
async def start_youtube(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    url = sanitize_url(data.get("url"))
    format_id = data.get("format_id")

    def hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            progress["download"] = min(downloaded / total * 100, 100)
        elif d['status'] == 'finished':
            progress["download"] = 100

    def process():
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                available_ids = [f["format_id"] for f in info.get("formats", [])]

            selected_format = format_id if format_id in available_ids else "bestvideo+bestaudio/best"

            ydl_opts = {
                'format': selected_format,
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'progress_hooks': [hook],
                # 'ffmpeg_location': FFMPEG_EXE_PATH,
                'merge_output_format': 'mp4',   # ensure merge
                  # 🧠 Throttling to prevent 429
                'sleep_interval': 2,          # Wait 2 seconds between requests
                'max_sleep_interval': 5,      # Random sleep up to 5s
                'ratelimit': 500000,          # Max 500KB/s download speed
                'throttled_rate': 300000,     # Gradually reduce speed if needed
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_path = ydl.prepare_filename(info)
                progress["file"] = downloaded_path
                progress["convert"] = 100
        except Exception as e:
            progress["convert"] = -1
            print("Download error:", e)

    progress.update({"download": 0, "convert": 0, "file": ""})
    background_tasks.add_task(process)
    return {"status": "started"}


@app.get("/youtube/progress")
def get_youtube_progress():
    return progress

@app.get("/youtube/files")
def list_downloaded_files():
    if not os.path.exists(DOWNLOAD_DIR):
        return {"files": []}
    files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith((".mp3", ".mp4", ".webm"))]
    return {"files": files}

@app.get("/youtube/download")
def download_youtube_file(filename: str):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(file_path):
        return {"error": "File not found"}
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)
##############################################################################
from routers.whiteboard import router as whiteboard_router
# Include whiteboard router
app.include_router(whiteboard_router)


@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    # Your existing code to render index.html
    return templates.TemplateResponse("index.html", {
        "request": request,
        "templates": [],  # your templates_list
        "files": []       # your files_list
    })

# Add these pages
@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})

@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})
