import uuid
from utils.db_vm import list_databases_vm, list_tables_vm, describe_table_vm
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

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app = FastAPI(title="Dynamic HLD Generator")
app.include_router(templates_router)

from utils.txt_generator import extract_placeholders_txt, generate_txt_file, preview_txt_file
# Serve static files (optional for JS/CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")
# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")
# include routers



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
from io import BytesIO
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



@app.get("/download/{filename}", summary="Download generated document")
def download_document(filename: str):
    """
    Serve the generated HLD document.
    """
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename
    )
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
from utils.txt_generator import extract_placeholders_txt, generate_txt_file, preview_txt_file


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
    output_file = os.path.join(OUTPUT_DIR, f"{uuid.uuid4().hex}_{payload.template}")

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


# Route for dbpage.html
@app.get("/dbpage", response_class=HTMLResponse)
async def dbpage(request: Request):
    return templates.TemplateResponse("dbpage.html", {"request": request})


@app.post("/connectVM")
async def connect_vm(request: Request):
    data = await request.json()
    ip = data.get("ip")
    user = data.get("user")
    password = data.get("password")

    if not all([ip, user, password]):
        return JSONResponse(content={"success": False, "message": "All fields required"}, status_code=400)

    try:
        # Try SSH connection
        ssh = test_connection(ip, user, password)
        if ssh:
            ssh.close()
        return JSONResponse(content={"success": True, "message": f"VM {ip} connected successfully!"})
    except Exception as e:
        return JSONResponse(content={"success": False, "message": f"Connection failed: {str(e)}"}, status_code=401)
# Store DB connection info globally simplest way for demo)
db_credentials = {}

# ---------- DB Connection ----------
db_config = {}  # global dict to store DB connection info

@app.post("/connect-db")
async def connect_db(request: Request):
    global db_config
    data = await request.json()
    try:
        # Save credentials for later
        db_config = {
            "host": data["host"],
            "port": data["port"],
            "user": data["user"],
            "password": data["password"]
        }
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [db[0] for db in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {"success": True, "databases": databases}
    except Exception as e:
        return {"success": False, "message": str(e)}

# ---------- List Tables ----------
# ---------- List Tables ----------
@app.get("/tables")
def list_tables(db_name: str):
    if not db_config:
        raise HTTPException(status_code=400, detail="DB not connected")

    conn = get_connection(database=db_name)
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES;")
    tables = [t[0] for t in cursor.fetchall()]
    conn.close()
    return {"tables": tables}

# ---------- Table Details ----------
@app.get("/table-details")
def table_details(db_name: str, table_name: str):
    if not db_config:
        raise HTTPException(status_code=400, detail="DB not connected")

    conn = get_connection(database=db_name)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"DESCRIBE {table_name};")
    details = cursor.fetchall()
    conn.close()
    return {"details": details}

# ---------- Create DB ----------
@app.post("/create-db")
async def create_db(request: Request):
    data = await request.json()
    db_name = data.get("db_name")
    if not db_name:
        raise HTTPException(status_code=400, detail="DB name required")
    if not db_credentials:
        raise HTTPException(status_code=400, detail="DB not connected")
    conn = mysql.connector.connect(
        host=db_credentials["host"],
        port=db_credentials["port"],
        user=db_credentials["user"],
        password=db_credentials["password"]
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE {db_name};")
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Database '{db_name}' created successfully!"}

@app.post("/create-table")
async def create_table(request: Request):
    data = await request.json()
    db_name = data.get("db_name")
    table_name = data.get("table_name")
    columns_str = data.get("columns")

    if not all([db_name, table_name, columns_str]):
        raise HTTPException(status_code=400, detail="DB name, table name, and columns are required")
    if not db_credentials:
        raise HTTPException(status_code=400, detail="DB not connected")

    # Convert columns string to SQL
    try:
        columns_list = []
        for col in columns_str.split(","):
            col_name, col_type = col.split(":")
            columns_list.append(f"{col_name.strip()} {col_type.strip()}")
        columns_sql = ", ".join(columns_list)
        create_table_sql = f"CREATE TABLE {table_name} ({columns_sql});"
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid columns format: {str(e)}")

    try:
        conn = mysql.connector.connect(
            host=db_credentials["host"],
            port=db_credentials["port"],
            user=db_credentials["user"],
            password=db_credentials["password"],
            database=db_name
        )
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        conn.commit()
        conn.close()
        return {"success": True, "message": f"Table '{table_name}' created successfully!"}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Failed to create table: {str(e)}")


# # Helper function to connect to DB
# def get_connection(host, port, user, password, database=None):
#     return mysql.connector.connect(
#         host=host, port=port, user=user, password=password, database=database
#     )

# -------- DB Connection Helper --------
def get_connection(database=None):
    if not db_config:
        raise Exception("Database not connected. Please connect first.")
    cfg = db_config.copy()
    if database:
        cfg["database"] = database
    return mysql.connector.connect(**cfg)

# -------- Delete Database --------
@app.post("/delete-db")
async def delete_db(request: Request):
    data = await request.json()
    db_name = data.get("db_name")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE `{db_name}`")
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "message": f"Database '{db_name}' deleted successfully."}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/delete-table")
async def delete_table(request: Request):
    data = await request.json()
    db_name = data.get("db_name")
    table_name = data.get("table_name")
    try:
        conn = get_connection(database=db_name)
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE `{table_name}`")
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "message": f"Table '{table_name}' deleted successfully."}
    except Exception as e:
        return {"success": False, "message": str(e)}


###########################################################################
