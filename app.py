print("APP STARTING...")
import json, uuid, os
from pathlib import Path

# Load .env automatically
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
    print("  .env loaded")
except ImportError:
    pass

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from detector import CrackDetector
from ai_analysis import analyse_with_claude, get_env_api_key

BASE_DIR     = Path(__file__).parent
UPLOAD_DIR   = BASE_DIR / "static" / "uploads"
RESULTS_DIR  = BASE_DIR / "static" / "results"
HISTORY_FILE = BASE_DIR / "static" / "history.json"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.secret_key = "railguard-2026"
CORS(app)

detector = CrackDetector(conf_threshold=0.55)

# In-memory: detection_id → {result, history, ann_path}
sessions: dict = {}

def load_history():
    if HISTORY_FILE.exists():
        try: return json.loads(HISTORY_FILE.read_text())
        except: pass
    return []

def save_history(h): HISTORY_FILE.write_text(json.dumps(h, indent=2))
def allowed(f): return Path(f).suffix.lower() in ALLOWED_EXT

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/detect", methods=["POST"])
def api_detect():
    if "file" not in request.files: return jsonify({"error":"No file"}), 400
    file = request.files["file"]
    if not file.filename or not allowed(file.filename):
        return jsonify({"error":"Invalid file type"}), 400
    ext      = Path(secure_filename(file.filename)).suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    img_path = UPLOAD_DIR / filename
    file.save(str(img_path))
    try:
        result = detector.detect(str(img_path))
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Detection failed: {e}"}), 500

    result["upload_filename"] = filename
    result["original_url"]    = f"/static/uploads/{filename}"
    result["annotated_url"]   = f"/static/{result['annotated_image']}"

    det_id = result["id"]
    sessions[det_id] = {
        "result":   result,
        "history":  [],
        "ann_path": str(BASE_DIR / "static" / result["annotated_image"]),
    }

    h = load_history()
    h.insert(0, {"id": det_id, "timestamp": result["timestamp"],
                  "severity": result["severity"], "detections": result["detection_count"],
                  "original_url": result["original_url"], "annotated_url": result["annotated_url"],
                  "advisory_heading": result["advisory"]["heading"]})
    save_history(h[:50])
    return jsonify(result)

@app.route("/api/ai-analyse", methods=["POST"])
def api_ai_analyse():
    body     = request.get_json(silent=True) or {}
    det_id   = body.get("detection_id", "")
    api_key  = body.get("api_key", "").strip() or get_env_api_key()
    question = body.get("question", None)
    if not api_key:
        return jsonify({"success": False, "error": "No API key — add it in the UI or set ANTHROPIC_API_KEY in .env"}), 400
    sess = sessions.get(det_id)
    if not sess:
        return jsonify({"success": False, "error": "Session not found — re-run detection."}), 404
    result = analyse_with_claude(
        detection_result=sess["result"],
        annotated_image_path=sess["ann_path"],
        api_key=api_key,
        follow_up_question=question,
        conversation_history=sess["history"] if question else None,
    )
    if result.get("success"):
        sessions[det_id]["history"] = result.get("history", [])
    return jsonify(result)

@app.route("/api/history")
def api_history(): return jsonify(load_history())

@app.route("/api/history/clear", methods=["POST"])
def api_clear_history():
    save_history([])
    return jsonify({"status": "cleared"})

@app.route("/api/model-info")
def api_model_info():
    return jsonify({"model_path": str(detector.model_path),
                    "conf_threshold": detector.conf_threshold, "model_type": "YOLOv8"})

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(str(BASE_DIR / "static"), filename)

if __name__ == "__main__":
    print("="*60)
    print("  RailGuard — Crack Detection + AI Analysis")
    print("="*60)
    print(f"  Model: {detector.model_path}")
    print(f"  URL  : http://localhost:5000")
    print("="*60)
    app.run(host="0.0.0.0", port=5000, debug=True)