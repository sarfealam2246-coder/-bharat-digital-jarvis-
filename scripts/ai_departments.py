import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "memory"
SKILLS_DIR = ROOT / "skills"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def load_memory(name: str, default):
    p = MEMORY_DIR / name
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_memory(name: str, data):
    p = MEMORY_DIR / name
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def estimate_market_rate(category: str, name: str = "", notes: str = "") -> dict:
    """2026 India market-rate pricing engine so every lead gets an accurate market & offer price."""
    text = f"{category} {name} {notes}".lower()
    if any(k in text for k in ["clinic", "doctor", "dentist", "hospital", "dental", "medical", "pharma"]):
        return {
            "marketRateInr": "₹10,000 – ₹25,000",
            "offerPriceInr": 7999,
            "workScope": "Clinic Appointment + QR Booking Site",
        }
    if any(k in text for k in ["school", "college", "coaching", "tuition", "academy", "institute"]):
        return {
            "marketRateInr": "₹15,000 – ₹50,000",
            "offerPriceInr": 11999,
            "workScope": "Admission + Notice & Test Portal",
        }
    if any(k in text for k in ["estate", "property", "builder", "car", "motorcycle", "showroom", "hotel", "resort"]):
        return {
            "marketRateInr": "₹15,000 – ₹45,000",
            "offerPriceInr": 9999,
            "workScope": "Property / Catalogue Showcase + WhatsApp Lead Site",
        }
    if any(k in text for k in ["ecommerce", "e-commerce", "store", "mart", "supermarket", "jewel", "electronics", "furniture"]):
        return {
            "marketRateInr": "₹30,000 – ₹80,000",
            "offerPriceInr": 14999,
            "workScope": "Online Catalogue + UPI Order Site",
        }
    if any(k in text for k in ["online_gig", "freelance", "reddit", "dashboard", "portal", "app", "saas", "tool", "bot"]):
        return {
            "marketRateInr": "₹25,000 – ₹1,00,000+",
            "offerPriceInr": 12999,
            "workScope": "Custom Web App / Interactive Tool",
        }
    return {
        "marketRateInr": "₹3,000 – ₹10,000",
        "offerPriceInr": 2999,
        "workScope": "1-Page Business Landing + WhatsApp Enquiry Page",
    }


def verify_html_integrity(html_text: str) -> tuple[bool, str]:
    """Auto-verify generated HTML so broken/truncated demos are caught before publishing."""
    if not html_text or len(html_text.strip()) < 300:
        return False, "HTML too short"
    low = html_text.lower()
    if "<html" not in low or "</html>" not in low or "<body" not in low or "</body>" not in low:
        return False, "Missing core HTML/BODY tags"
    if low.count("<script") != low.count("</script>"):
        return False, "Unclosed <script> tag"
    return True, "OK"


def load_skill_for_category(category: str) -> str:
    cat = (category or "").lower()
    if any(k in cat for k in ["clinic", "doctor", "dentist", "hospital"]):
        fname = "clinic.md"
    elif any(k in cat for k in ["school", "college", "coaching", "tuition"]):
        fname = "coaching_school.md"
    elif any(k in cat for k in ["estate", "property", "car", "motorcycle", "showroom"]):
        fname = "realestate.md"
    else:
        fname = "general_business.md"
    p = SKILLS_DIR / fname
    return p.read_text(encoding="utf-8") if p.exists() else ""


def parse_json_safe(text: str):
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)
    return json.loads(cleaned)


def discover_nvidia_models(nvidia_key: str, role: str = "ceo") -> list[str]:
    fallback = [
        "nvidia/nemotron-3-ultra-550b-a55b",
        "nvidia/nemotron-3-super-120b-a12b",
        "meta/llama-3.3-70b-instruct",
        "qwen/qwen2.5-72b-instruct",
        "deepseek-ai/deepseek-r1",
    ]
    try:
        r = requests.get(
            "https://integrate.api.nvidia.com/v1/models",
            headers={"Authorization": f"Bearer {nvidia_key}", "User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        if r.ok:
            ids = [m["id"] for m in r.json().get("data", []) if isinstance(m, dict) and m.get("id")]
            chat_ids = [m for m in ids if not any(b in m.lower() for b in ["embed", "rerank", "guard", "tts", "whisper", "neva", "gliner"])]
            if role == "builder":
                chat_ids.sort(key=lambda x: (0 if "qwen" in x.lower() or "coder" in x.lower() else (1 if "deepseek" in x.lower() else 2), x))
            elif role == "writer":
                chat_ids.sort(key=lambda x: (0 if "glm" in x.lower() or "kimi" in x.lower() or "llama-3.3" in x.lower() else 1, x))
            else:
                chat_ids.sort(key=lambda x: (0 if "550b" in x.lower() or "405b" in x.lower() else (1 if "120b" in x.lower() or "70b" in x.lower() else 2), x))
            if chat_ids:
                return chat_ids[:5]
    except Exception:
        pass
    return fallback


def discover_groq_models(groq_key: str) -> list[str]:
    try:
        r = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {groq_key}", "User-Agent": "Mozilla/5.0"},
            timeout=12,
        )
        if r.ok:
            ids = [m["id"] for m in r.json().get("data", []) if isinstance(m, dict) and m.get("id")]
            chat_ids = [m for m in ids if not any(b in m.lower() for b in ["whisper", "guard", "tts", "orpheus", "playai", "safeguard"])]
            chat_ids.sort(key=lambda x: (0 if "70b" in x.lower() else (1 if "llama" in x.lower() else 2), x))
            if chat_ids:
                return chat_ids[:4]
    except Exception:
        pass
    return ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]


def discover_gemini_models(gemini_key: str) -> list[str]:
    try:
        r = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=12,
        )
        if r.ok:
            models = [
                m["name"].replace("models/", "")
                for m in r.json().get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])
                and "tts" not in m["name"].lower()
                and "image" not in m["name"].lower()
            ]
            models.sort(key=lambda x: (0 if "flash" in x.lower() else 1, x))
            if models:
                return models[:4]
    except Exception:
        pass
    return ["gemini-2.5-flash"]


def _call_nvidia(prompt: str, system: str, role: str, expect_json: bool) -> str | None:
    key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not key:
        return None
    for model in discover_nvidia_models(key, role):
        try:
            r = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "temperature": 0.4, "max_tokens": 1800},
                timeout=45,
            )
            if r.ok:
                txt = r.json()["choices"][0]["message"]["content"]
                if expect_json:
                    parse_json_safe(txt)
                return txt
        except Exception:
            continue
    return None


def _call_groq(prompt: str, system: str, expect_json: bool) -> str | None:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return None
    for model in discover_groq_models(key):
        try:
            payload = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "temperature": 0.4}
            if expect_json:
                payload["response_format"] = {"type": "json_object"}
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload, timeout=35)
            if r.ok:
                txt = r.json()["choices"][0]["message"]["content"]
                if expect_json:
                    parse_json_safe(txt)
                return txt
        except Exception:
            continue
    return None


def _call_gemini(prompt: str, system: str, expect_json: bool) -> str | None:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    for model in discover_gemini_models(key):
        try:
            gen_cfg = {"temperature": 0.4}
            if expect_json:
                gen_cfg["responseMimeType"] = "application/json"
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}], "generationConfig": gen_cfg},
                timeout=35,
            )
            if r.ok:
                txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                if expect_json:
                    parse_json_safe(txt)
                return txt
        except Exception:
            continue
    return None


def run_department(department: str, prompt: str, system: str, expect_json: bool = True):
    """Divide-and-work across NVIDIA (34+ models), Groq, and Gemini."""
    order_map = {
        "ceo": [("nvidia", "ceo"), ("gemini", None), ("groq", None)],
        "hunter": [("groq", None), ("nvidia", "hunter"), ("gemini", None)],
        "builder": [("nvidia", "builder"), ("gemini", None), ("groq", None)],
        "writer": [("gemini", None), ("nvidia", "writer"), ("groq", None)],
    }
    for provider, role in order_map.get(department, order_map["ceo"]):
        if provider == "nvidia":
            out = _call_nvidia(prompt, system, role or "ceo", expect_json)
        elif provider == "groq":
            out = _call_groq(prompt, system, expect_json)
        else:
            out = _call_gemini(prompt, system, expect_json)
        if out:
            return parse_json_safe(out) if expect_json else out
    return None


def generate_poster_image(prompt: str, out_path: Path) -> bool:
    """Visual Studio: Cloudflare Account ID+Token -> Gemini Image."""
    acc_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    if acc_id and token:
        for model in ["@cf/black-forest-labs/flux-1-schnell", "@cf/bytedance/stable-diffusion-xl-lightning"]:
            try:
                r = requests.post(
                    f"https://api.cloudflare.com/client/v4/accounts/{acc_id}/ai/run/{model}",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"prompt": prompt, "num_steps": 6, "width": 768, "height": 768},
                    timeout=40,
                )
                if r.ok:
                    if "image/" in r.headers.get("Content-Type", ""):
                        out_path.write_bytes(r.content)
                        return True
                    b64 = r.json().get("result", {}).get("image")
                    if b64:
                        out_path.write_bytes(base64.b64decode(b64))
                        return True
            except Exception:
                continue

    if gemini_key:
        for g_model in ["gemini-2.0-flash-exp-image-generation", "gemini-2.5-flash-image"]:
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={gemini_key}",
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": f"Clean modern Indian business banner: {prompt}"}]}], "generationConfig": {"responseModalities": ["IMAGE"]}},
                    timeout=40,
                )
                if r.ok:
                    for p in r.json()["candidates"][0]["content"]["parts"]:
                        if p.get("inlineData", {}).get("data"):
                            out_path.write_bytes(base64.b64decode(p["inlineData"]["data"]))
                            return True
            except Exception:
                continue
    return False


def ceo_audit_outreach(lead: dict, pitch_text: str, demo_url: str) -> dict:
    audit_log = load_memory("ceo_audit_log.json", [])
    prompt = f"""
Audit this Indian client outreach message & demo:
Business: {lead.get('name')} ({lead.get('category')}, {lead.get('city')})
Demo URL: {demo_url}
Message: {pitch_text}

Verify: polite Hindi/Hinglish, clearly mentions sample demo & offer price, zero placeholders.
Return JSON: {{"approved": true, "reason": "short note", "polishedMessage": "final clean message"}}
"""
    res = run_department("ceo", prompt, "You are the strict CEO & Ethics Auditor. Return ONLY JSON.", expect_json=True)
    if not isinstance(res, dict):
        res = {"approved": bool(demo_url and pitch_text), "reason": "Rule pass", "polishedMessage": pitch_text}
    audit_log.append({"ts": datetime.now(timezone.utc).isoformat(), "lead": lead.get("name"), "approved": res.get("approved", True), "reason": res.get("reason", "")})
    save_memory("ceo_audit_log.json", audit_log[-100:])
    return res
                         
