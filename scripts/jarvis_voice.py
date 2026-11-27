import asyncio
import base64
import os
import subprocess
import wave
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


async def _edge_tts_save(text: str, out_mp3: Path):
    import edge_tts
    comm = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="+4%", pitch="-3Hz")
    await comm.save(str(out_mp3))


def generate_jarvis_brief_mp3(hindi_text: str, out_mp3: Path | None = None) -> bool:
    """Generates natural Hindi Jarvis voice brief (Gemini TTS -> edge-tts -> gTTS)."""
    target = out_mp3 or (MEMORY_DIR / "jarvis_brief.mp3")
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        for model in ["gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"]:
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}",
                    json={
                        "contents": [{"parts": [{"text": f"Speak in a calm, confident, natural Hindi assistant (Jarvis) voice: {hindi_text}"}]}],
                        "generationConfig": {
                            "responseModalities": ["AUDIO"],
                            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Charon"}}},
                        },
                    },
                    timeout=40,
                )
                if r.ok:
                    for p in r.json()["candidates"][0]["content"]["parts"]:
                        data = p.get("inlineData", {}).get("data")
                        if data:
                            tmp_wav = target.with_suffix(".wav")
                            with wave.open(str(tmp_wav), "wb") as wf:
                                wf.setnchannels(1)
                                wf.setsampwidth(2)
                                wf.setframerate(24000)
                                wf.writeframes(base64.b64decode(data))
                            subprocess.run(["ffmpeg", "-y", "-i", str(tmp_wav), "-b:a", "96k", str(target)], check=True, capture_output=True)
                            tmp_wav.unlink(missing_ok=True)
                            return True
            except Exception:
                continue

    try:
        asyncio.run(_edge_tts_save(hindi_text, target))
        if target.exists() and target.stat().st_size > 4000:
            return True
    except Exception:
        pass

    try:
        from gtts import gTTS
        gTTS(text=hindi_text, lang="hi", slow=False).save(str(target))
        return target.exists() and target.stat().st_size > 2000
    except Exception:
        return False
