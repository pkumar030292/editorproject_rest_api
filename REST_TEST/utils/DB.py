from datetime import datetime
from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
from .upload_temp import router as templates_router
from .accesstovm import test_connection
from .config import TEMPLATE_DIR
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import mysql.connector
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory="templates")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
DB_ACTIONS = APIRouter()
DB_ACTIONS.include_router(templates_router)

# Serve static files (optional for JS/CSS)
DB_ACTIONS.mount("/static", StaticFiles(directory="static"), name="static")
# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")
# include routers

# Route for dbpage.html
@DB_ACTIONS.get("/dbpage", response_class=HTMLResponse)
async def dbpage(request: Request):
    return templates.TemplateResponse("dbpage.html", {"request": request})


@DB_ACTIONS.post("/connectVM")
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

@DB_ACTIONS.post("/connect-db")
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
@DB_ACTIONS.get("/tables")
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
@DB_ACTIONS.get("/table-details")
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
@DB_ACTIONS.post("/create-db")
async def create_db(request: Request):
    global db_config
    if not db_config:
        return {"success": False, "message": "DB not connected"}
    data = await request.json()
    db_name = data.get("db_name")
    if not db_name:
        return {"success": False, "message": "DB name required"}

    try:
        conn = mysql.connector.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"]
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE `{db_name}`;")
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "message": f"Database '{db_name}' created successfully!"}
    except mysql.connector.Error as e:
        # Return MySQL error message to frontend
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}

# ---------- Create Table ----------
# ---------- Create Table ----------
@DB_ACTIONS.post("/create-table")
async def create_table(request: Request):
    global db_config
    if not db_config:
        return {"success": False, "message": "DB not connected"}

    data = await request.json()
    db_name = data.get("db_name")
    table_name = data.get("table_name")
    columns_str = data.get("columns")

    if not all([db_name, table_name, columns_str]):
        return {"success": False, "message": "DB name, table name, and columns are required"}

    try:
        columns_list = []
        for col in columns_str.split(","):
            col_name, col_type = col.split(":")
            columns_list.append(f"`{col_name.strip()}` {col_type.strip()}")
        columns_sql = ", ".join(columns_list)
        create_table_sql = f"CREATE TABLE `{table_name}` ({columns_sql});"
    except Exception as e:
        return {"success": False, "message": f"Invalid columns format: {str(e)}"}

    try:
        conn = mysql.connector.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_name
        )
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "message": f"Table '{table_name}' created successfully!"}
    except mysql.connector.Error as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}

# # Helper function to connect to DB
# def get_connection(host, port, user, password, database=None):
#     return mysql.connector.connect(
#         host=host, port=port, user=user, password=password, database=database
#     )

# -------- DB Connection Helper --------
def get_connection(database=None):
    if not db_config:
        raise Exception("Contact to system Admin to get access to DB to delete Template.")
    cfg = db_config.copy()
    # Force database to 'admin_users' if not specified
    cfg["database"] = database or "admin_users"
    return mysql.connector.connect(**cfg)


# -------- Delete Database --------
# ---------- Delete Database ----------
@DB_ACTIONS.post("/delete-db")
async def delete_db(request: Request):
    data = await request.json()
    db_name = data.get("db_name")
    if not db_name:
        return {"success": False, "message": "Database name required"}
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE `{db_name}`")
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "message": f"Database '{db_name}' deleted successfully."}
    except mysql.connector.Error as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}
# ---------- Delete Table ----------
@DB_ACTIONS.post("/delete-table")
async def delete_table(request: Request):
    data = await request.json()
    db_name = data.get("db_name")
    table_name = data.get("table_name")
    if not all([db_name, table_name]):
        return {"success": False, "message": "Database and table name required"}
    try:
        conn = get_connection(database=db_name)
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE `{table_name}`")
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "message": f"Table '{table_name}' deleted successfully."}
    except mysql.connector.Error as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}

###########################################################################


# Use your existing get_connection helper
def validate_user_password(username: str, password: str):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if not user:
            return False
        db_password = user["password"]
        return password == db_password  # For production, use hashed password check!
    except Exception:
        return False
###
# ---------- Delete Template ----------
@DB_ACTIONS.post("/delete-template")
async def delete_template(request: Request):
    data = await request.json()
    template_name = data.get("template_name")
    username = data.get("username")
    password = data.get("password")
    if not all([template_name, username, password]):
        return {"success": False, "message": "Template, username, and password required"}

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM admin_users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if not user:
            return {"success": False, "message": "Invalid username or password"}
    except mysql.connector.Error as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}

    template_path = TEMPLATE_DIR / template_name
    if template_path.exists() and template_path.is_file():
        try:
            template_path.unlink()
            return {"success": True, "message": f"Template '{template_name}' deleted successfully."}
        except Exception as e:
            return {"success": False, "message": f"Failed to delete template: {str(e)}"}
    else:
        return {"success": False, "message": "Template file does not exist"}

####################################################30-09-2025

# ---------- Create Admin ----------
@DB_ACTIONS.post("/create-admin")
async def create_admin(request: Request):
    data = await request.json()
    db_name = data.get("db_name")
    password = data.get("password")
    if not all([db_name, password]):
        return {"success": False, "message": "DB name and password required"}
    try:
        conn = get_connection(database=db_name)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO admin (password, created_at) VALUES (%s, %s)",
            (password, datetime.now())
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "message": "Admin user created successfully!"}
    except mysql.connector.Error as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}


##########################

# ---------- Insert Row ----------
@DB_ACTIONS.post("/insert-row")
async def insert_row(request: Request):
    data = await request.json()
    db_name = data.get("db_name")
    table_name = data.get("table_name")
    row_data = data.get("row_data")
    if not all([db_name, table_name, row_data]):
        return {"success": False, "message": "DB, table, and row data required"}

    try:
        # Auto-fill created_at if exists but empty
        if "created_at" in row_data and not row_data["created_at"]:
            row_data["created_at"] = datetime.now()

        conn = get_connection(database=db_name)
        cursor = conn.cursor()
        columns = ", ".join(f"`{col}`" for col in row_data.keys())
        placeholders = ", ".join(["%s"] * len(row_data))
        values = list(row_data.values())
        sql = f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "message": f"Row inserted into '{table_name}' successfully."}
    except mysql.connector.Error as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}


@DB_ACTIONS.get("/table-data")
def table_data(db_name: str, table_name: str):
    if not db_config:
        raise HTTPException(status_code=400, detail="DB not connected")
    try:
        conn = get_connection(database=db_name)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 100")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"success": True, "rows": rows}
    except Exception as e:
        return {"success": False, "rows": [], "error": str(e)}