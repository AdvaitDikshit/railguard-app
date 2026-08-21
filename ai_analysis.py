"""
AI Analysis Module — sends crack detection results to Claude API
Loads API key from .env file automatically if present.
"""

import base64
import json
import os
from pathlib import Path

import requests

# Load .env file if present (pip install python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # dotenv not installed — key must be passed manually

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are a Senior Railway Track Engineer with 20+ years of experience 
in structural inspection, track maintenance, and safety compliance for heavy rail systems.

When given crack detection results and an image of a railway track, you provide:
1. A professional assessment of the crack type and likely cause
2. Structural risk evaluation
3. Specific maintenance recommendations
4. Any follow-up tests the field team should perform

Keep your response practical, specific, and concise. Use engineering terminology 
but explain it clearly. Format your response in clear sections using ** for headings.
Do NOT repeat information already in the detection report — add new expert insight."""


def get_env_api_key() -> str:
    """Return API key from environment if set, else empty string."""
    return os.environ.get("ANTHROPIC_API_KEY", "")


def analyse_with_claude(
    detection_result: dict,
    annotated_image_path: str,
    api_key: str,
    follow_up_question: str | None = None,
    conversation_history: list | None = None,
) -> dict:
    # Use env key as fallback if none passed from UI
    if not api_key:
        api_key = get_env_api_key()
    if not api_key:
        return {"success": False, "error": "No Claude API key provided."}

    # Encode annotated image
    img_b64 = None
    try:
        img_path = Path(annotated_image_path)
        if img_path.exists():
            with open(img_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"Image encode error: {e}")

    # Build detection summary
    dets    = detection_result.get("detections", [])
    profile = detection_result.get("crack_profile", {})
    sev     = detection_result.get("severity", "UNKNOWN")
    advisory = detection_result.get("advisory", {})

    det_lines = ""
    for i, d in enumerate(dets, 1):
        det_lines += (
            f"\n  {i}. {d['class_name']} | conf={d['confidence']:.1%} | "
            f"size={d.get('size_cat','?')} | "
            f"{d.get('width_px',0)}×{d.get('height_px',0)}px | "
            f"area={d['area_frac']*100:.2f}%"
        )

    context = f"""
DETECTION SUMMARY
─────────────────
Severity      : {sev}
Total cracks  : {detection_result.get('detection_count', 0)}
Largest crack : {profile.get('size_cat','—').upper()} ({profile.get('max_area_pct',0):.2f}% of image)
Max confidence: {profile.get('max_conf',0):.1%}
Advisory      : {advisory.get('heading','—')}

DETECTIONS:{det_lines if det_lines else chr(10)+'  None'}

Image: {detection_result.get('image_size',{}).get('width','?')}×{detection_result.get('image_size',{}).get('height','?')}px
"""

    if follow_up_question:
        user_text = f"Follow-up from inspection engineer:\n\n{follow_up_question}"
    else:
        user_text = (
            f"Analyse this railway track inspection and provide expert assessment.\n\n"
            f"{context}\n\n"
            "Please provide:\n"
            "**1. Crack Type & Likely Cause** — what type of crack and why does it form?\n"
            "**2. Structural Risk** — how serious is this if left untreated?\n"
            "**3. Recommended Repair** — specific repair method for this crack type\n"
            "**4. Field Tests Required** — what physical tests should the team do on-site?\n"
            "**5. Severity Agreement** — do you agree with the AI severity, or would you change it?"
        )

    content = []
    if img_b64:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}
        })
    content.append({"type": "text", "text": user_text})

    messages = []
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": content})

    headers = {
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model":    CLAUDE_MODEL,
        "max_tokens": 1200,
        "system":   SYSTEM_PROMPT,
        "messages": messages,
    }

    try:
        resp = requests.post(CLAUDE_API_URL, headers=headers,
                             data=json.dumps(payload), timeout=45)
        resp.raise_for_status()
        data = resp.json()

        analysis = "".join(
            b["text"] for b in data.get("content", []) if b.get("type") == "text"
        )

        new_history = messages + [{"role": "assistant", "content": analysis}]

        return {
            "success":  True,
            "analysis": analysis,
            "model":    data.get("model", CLAUDE_MODEL),
            "history":  new_history,
        }

    except requests.exceptions.HTTPError as e:
        try:    msg = e.response.json().get("error", {}).get("message", str(e))
        except: msg = str(e)
        return {"success": False, "error": f"API error: {msg}"}
    except Exception as e:
        return {"success": False, "error": str(e)}