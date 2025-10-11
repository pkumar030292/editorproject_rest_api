# utils/config.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # REST_TEST
TEMPLATE_DIR = BASE_DIR / "templates/SampleTemplates"
OUTPUT_DIR = BASE_DIR / "Generated_files"

TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("OUTPUT_DIR111:", OUTPUT_DIR)
