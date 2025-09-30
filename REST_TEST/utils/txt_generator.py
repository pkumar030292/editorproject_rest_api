import os
import uuid
from pathlib import Path
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def extract_placeholders_txt(file_path: str) -> list:
    """
    Extract placeholders from a .txt file.
    Placeholders are defined as {{placeholder_name}}
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{file_path}' not found")

    placeholders = set()
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            while "{{" in line and "}}" in line:
                start = line.find("{{") + 2
                end = line.find("}}")
                placeholders.add(line[start:end].strip())
                line = line[end+2:]
    return list(placeholders)

def generate_txt_file(template_path: str, fields: Dict[str, str], output_dir: str) -> str:
    """
    Generate a .txt file from a template with placeholders replaced.
    Returns the generated filename.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template '{template_path}' not found")

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace placeholders
    for key, value in fields.items():
        placeholder = f"{{{{{key}}}}}"  # e.g., {{project_name}}
        content = content.replace(placeholder, value)

    # Generate unique filename
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{Path(template_path).stem}_{uuid.uuid4().hex[:8]}.txt"
    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logging.info(f"Generated TXT file: {output_path}")
    return filename

def preview_txt_file(template_path: str, fields: Dict[str, str]) -> str:
    """
    Return the filled content of a .txt template without saving.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template '{template_path}' not found")

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    for key, value in fields.items():
        placeholder = f"{{{{{key}}}}}"
        content = content.replace(placeholder, value)

    return content

