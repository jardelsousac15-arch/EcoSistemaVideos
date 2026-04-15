"""
APP 02 · PROMPTGEN SERVICE
Recebe frames do Frameshot e gera prompts via Claude (Anthropic API)
Regras: 2D cartoon, bold outlines, 9:16 full-bleed, sem preto/branco, sem sunset, sem bordas
"""

import asyncio
import httpx
from datetime import datetime


SYSTEM_PROMPT = """You are an expert AI image prompt engineer for 2D cartoon TikTok content.

STRICT MANDATORY RULES — never break these:
1. ALWAYS include: "2D cartoon style, bold thick outlines, strong clean line art"
2. ALWAYS include: "9:16 vertical format, full-bleed, entire frame filled edge-to-edge, zero white borders, zero margins"
3. ALWAYS include: "vibrant saturated colors, full-color palette"
4. NEVER mention or imply: black and white, grayscale, monochrome, sepia, muted tones, desaturated
5. NEVER mention: sunset, golden hour, dusk, dawn, twilight
6. NEVER mention: white borders, vignette, letterbox, pillarbox, margins, padding
7. Output ONLY the prompt text — no explanation, no preamble, no numbering
8. Language: English only
9. Length: 60-100 words, vivid and specific
10. Style must feel like Cartoon Network or bold graphic novel illustration"""

PT_NOTES = [
    "Cena totalmente preenchida, sem bordas ou margens brancas.",
    "Traços grossos e expressivos no estilo cartoon 2D.",
    "Paleta de cores vibrante e saturada, sem preto e branco.",
    "Formato vertical 9:16 com a imagem ocupando todo o quadro.",
    "Sem pôr do sol — iluminação viva e artificial ou luz do dia intensa.",
    "Personagens com contornos fortes, estilo cartoon moderno.",
    "Cores primárias ousadas dominando toda a composição.",
    "Estilo cartoon 2D com traços limpos e linhas de contorno expressivas.",
    "Nada de filtros desbotados — tudo vivo, colorido e cheio de energia.",
]

FORBIDDEN = ["black and white", "grayscale", "monochrome", "sunset", "golden hour",
             "white border", "vignette", "letterbox", "muted", "desaturated", "sepia"]


async def generate_prompts(frames_payload: dict, anthropic_api_key: str) -> dict:
    """
    Gera um prompt por frame usando Claude com visão.
    Retorna payload no formato promptgen_v1.
    """
    frames = frames_payload.get("frames", [])
    if not frames:
        raise ValueError("Nenhum frame encontrado no payload do Frameshot")

    prompts = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, frame in enumerate(frames):
            prompt_text = await _generate_single_prompt(client, frame, anthropic_api_key)
            prompt_text = _sanitize_prompt(prompt_text)

            prompts.append({
                "id": frame.get("id", i + 1),
                "timestamp": frame.get("timestamp", "--:--"),
                "filename": frame.get("filename", f"frame_{i+1:03d}.jpg"),
                "prompt": prompt_text,
                "pt_note": PT_NOTES[i % len(PT_NOTES)],
                "rules_applied": {
                    "style": "2D cartoon bold outlines",
                    "format": "9:16 full-bleed",
                    "forbidden_removed": True,
                    "language": "english"
                }
            })

            # Rate limiting gentil
            await asyncio.sleep(0.5)

    return {
        "source": "promptgen_v1",
        "schema_version": "1.0",
        "generated_at": datetime.utcnow().isoformat(),
        "prompt_count": len(prompts),
        "video_url": frames_payload.get("video_url", ""),
        "rules": {
            "style": "2D cartoon with bold thick outlines",
            "format": "9:16 full-bleed no borders",
            "forbidden": FORBIDDEN,
            "language": "english"
        },
        "prompts": prompts,
        "meta": {
            "app": "promptgen",
            "version": "1.0",
            "prev_app": "frameshot_v1",
            "next_apps": ["imagegen_v1"]
        }
    }


async def _generate_single_prompt(client: httpx.AsyncClient, frame: dict, api_key: str) -> str:
    """Chama a API do Gemini com a imagem do frame para gerar o prompt"""
    data_url = frame.get("data_url", "")
    
    parts = [{"text": "Generate a 2D cartoon image prompt based on this TikTok frame. Follow ALL rules strictly. Output only the prompt."}]

    if data_url and data_url.startswith("data:image"):
        media_type = data_url.split(";")[0].split(":")[1]
        b64_data = data_url.split(",")[1]
        parts.append({
            "inline_data": {
                "mime_type": media_type,
                "data": b64_data
            }
        })
    else:
        ts = frame.get("timestamp", "unknown")
        parts = [{"text": f"Generate a 2D cartoon image prompt for a TikTok frame at timestamp {ts}. Follow ALL rules strictly. Output only the prompt."}]

    response = await client.post(
        f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-latest:generateContent?key={api_key}",
        headers={"Content-Type": "application/json"},
        json={
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": parts}],
            "generationConfig": {"maxOutputTokens": 300}
        }
    )

    if response.status_code != 200:
        raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}")

    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected response from Gemini: {data}")


def _sanitize_prompt(text: str) -> str:
    """Remove qualquer menção às palavras proibidas e garante regras obrigatórias"""
    t = text
    for word in FORBIDDEN:
        import re
        t = re.sub(word, "", t, flags=re.IGNORECASE)

    if "2D cartoon" not in t and "2d cartoon" not in t.lower():
        t = "2D cartoon style with bold thick outlines, " + t

    if "9:16" not in t and "full-bleed" not in t:
        t += ", 9:16 vertical full-bleed format, entire frame filled edge-to-edge, no white borders"

    return " ".join(t.split()).strip()
