import os, json, datetime, base64

os.makedirs("outputs", exist_ok=True)
STROKE_FILE = "outputs/whiteboard_strokes.json"

def save_stroke(stroke: dict):
    strokes = []
    if os.path.exists(STROKE_FILE):
        with open(STROKE_FILE, "r") as f:
            try: strokes = json.load(f)
            except: strokes = []
    strokes.append(stroke)
    with open(STROKE_FILE, "w") as f:
        json.dump(strokes, f, indent=2)

def save_snapshot(data_url: str):
    header, encoded = data_url.split(",", 1)
    data = base64.b64decode(encoded)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"outputs/snapshot_{timestamp}.png"
    with open(filename, "wb") as f: f.write(data)
    return filename
