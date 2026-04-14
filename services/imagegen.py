"""
APP 03 · IMAGEGEN SERVICE
Recebe prompts do PromptGen e gera imagens via Gemini API (Imagen 3)
Formato: 9:16, full-bleed, cartoon 2D
"""

import asyncio
import httpx
import base64
from datetime import datetime


IMAGEN_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict"


async def generate_images(prompts_payload: dict, gemini_api_key: str) -> dict:
    """
    Gera uma imagem por prompt usando Gemini Imagen 3.
    Retorna payload no formato imagegen_v1.
    """
    prompts = prompts_payload.get("prompts", [])
    if not prompts:
        raise ValueError("Nenhum prompt encontrado no payload do PromptGen")

    images = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, p in enumerate(prompts):
            image_data = await _generate_single_image(client, p["prompt"], gemini_api_key)

            images.append({
                "id": p.get("id", i + 1),
                "timestamp": p.get("timestamp", "--:--"),
                "filename": _make_filename(p, i),
                "prompt": p.get("prompt", ""),
                "pt_note": p.get("pt_note", ""),
                "status": "success" if image_data else "error",
                "data_url": f"data:image/jpeg;base64,{image_data}" if image_data else None,
                "model": "imagen-3.0-generate-001",
                "aspect_ratio": "9:16"
            })

            # Respeita rate limit da API
            await asyncio.sleep(1.0)

    success_count = sum(1 for img in images if img["status"] == "success")

    return {
        "source": "imagegen_v1",
        "schema_version": "1.0",
        "generated_at": datetime.utcnow().isoformat(),
        "model": "imagen-3.0-generate-001",
        "aspect_ratio": "9:16",
        "total": len(images),
        "success_count": success_count,
        "error_count": len(images) - success_count,
        "video_url": prompts_payload.get("video_url", ""),
        "images": images,
        "meta": {
            "app": "imagegen",
            "version": "1.0",
            "prev_app": "promptgen_v1",
            "next_apps": ["content_scheduler", "auto_poster", "trend_analyzer"]
        }
    }


async def _generate_single_image(client: httpx.AsyncClient, prompt: str, api_key: str) -> str | None:
    """Chama a Gemini API e retorna a imagem em base64"""
    try:
        response = await client.post(
            f"{IMAGEN_ENDPOINT}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "instances": [{"prompt": prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "9:16",
                    "safetySetting": "block_some",
                    "addWatermark": False,
                    "outputMimeType": "image/jpeg"
                }
            }
        )

        if response.status_code != 200:
            print(f"[ImageGen] Gemini API error {response.status_code}: {response.text[:200]}")
            return None

        data = response.json()
        b64 = data.get("predictions", [{}])[0].get("bytesBase64Encoded")
        return b64

    except Exception as e:
        print(f"[ImageGen] Erro ao gerar imagem: {e}")
        return None


def _make_filename(prompt_obj: dict, idx: int) -> str:
    ts = prompt_obj.get("timestamp", "00:00").replace(":", "m")
    num = str(prompt_obj.get("id", idx + 1)).zfill(3)
    return f"imagegen_{num}_{ts}s.jpg"
