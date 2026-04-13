"""
APP 01 · FRAMESHOT SERVICE
Baixa vídeo do TikTok via yt-dlp e extrai frames com OpenCV
"""

import os
import cv2
import base64
import tempfile
import asyncio
from datetime import datetime


async def extract_frames(video_url: str, frame_count: int = 8, quality: int = 90) -> dict:
    """
    Baixa o vídeo TikTok e extrai frames uniformemente distribuídos.
    Retorna payload no formato frameshot_v1.
    """
    return await asyncio.get_event_loop().run_in_executor(
        None, _extract_sync, video_url, frame_count, quality
    )


def _extract_sync(video_url: str, frame_count: int, quality: int) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = _download_video(video_url, tmpdir)
        frames = _extract_frames_opencv(video_path, frame_count, quality)

    return {
        "source": "frameshot_v1",
        "schema_version": "1.0",
        "video_url": video_url,
        "extracted_at": datetime.utcnow().isoformat(),
        "frame_count": len(frames),
        "quality": quality,
        "frames": frames,
        "meta": {
            "app": "frameshot",
            "version": "1.0",
            "next_apps": ["promptgen_v1"]
        }
    }


def _download_video(url: str, output_dir: str) -> str:
    """Baixa o vídeo usando yt-dlp"""
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp não instalado. Execute: pip install yt-dlp")

    ydl_opts = {
        "outtmpl": os.path.join(output_dir, "video.%(ext)s"),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
        # Bypass TikTok restrictions
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            "Referer": "https://www.tiktok.com/",
        },
        "extractor_args": {
            "tiktok": {"webpage_download": True}
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Encontra o arquivo baixado
    for f in os.listdir(output_dir):
        if f.startswith("video"):
            return os.path.join(output_dir, f)

    raise RuntimeError("Arquivo de vídeo não encontrado após download")


def _extract_frames_opencv(video_path: str, frame_count: int, quality: int) -> list:
    """Extrai frames uniformemente distribuídos ao longo do vídeo"""
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError(f"Não foi possível abrir o vídeo: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    if total_frames <= 0:
        raise RuntimeError("Vídeo inválido ou sem frames")

    frames = []
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]

    for i in range(frame_count):
        # Distribui os frames uniformemente, evitando início e fim bruscos
        frame_idx = int(((i + 0.5) / frame_count) * total_frames)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()

        if not ret:
            continue

        # Encode para JPEG em base64
        _, buffer = cv2.imencode(".jpg", frame, encode_params)
        b64 = base64.b64encode(buffer).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64}"

        # Timestamp em minutos:segundos
        ts_sec = frame_idx / fps if fps > 0 else 0
        ts_label = f"{int(ts_sec // 60):02d}:{int(ts_sec % 60):02d}"

        frames.append({
            "id": i + 1,
            "frame_index": frame_idx,
            "timestamp": ts_label,
            "timestamp_seconds": round(ts_sec, 2),
            "filename": f"frame_{str(i+1).padStart(3, '0')}_{ts_label.replace(':', 'm')}s.jpg",
            "data_url": data_url,
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        })

    cap.release()

    if not frames:
        raise RuntimeError("Nenhum frame foi extraído do vídeo")

    return frames
