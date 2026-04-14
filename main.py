"""
ECOSYSTEM BACKEND — API central do ecossistema TikTok
Conecta APP 01 (Frameshot) → APP 02 (PromptGen) → APP 03 (ImageGen)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import asyncio
from datetime import datetime
import os

from services.frameshot import extract_frames
from services.promptgen import generate_prompts
from services.imagegen import generate_images

app = FastAPI(
    title="Ecosystem API",
    description="Pipeline TikTok → Frames → Prompts → Imagens",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Jobs em memória
jobs: dict = {}


# ─── MODELS ───────────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    video_url: str
    frame_count: int = 8
    quality: int = 90
    gemini_api_key: str
    anthropic_api_key: str

class FramesOnlyRequest(BaseModel):
    video_url: str
    frame_count: int = 8
    quality: int = 90

class PromptsOnlyRequest(BaseModel):
    frames_payload: dict
    anthropic_api_key: str

class ImagesOnlyRequest(BaseModel):
    prompts_payload: dict
    gemini_api_key: str


# ─── HEALTH ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "online",
        "version": "1.0.0",
        "apps": ["frameshot_v1", "promptgen_v1", "imagegen_v1"],
        "endpoints": ["/pipeline", "/frames", "/prompts", "/images", "/job/{id}"]
    }

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ─── APP 01: FRAMESHOT ────────────────────────────────────────────────────────

@app.post("/frames")
async def app01_extract_frames(req: FramesOnlyRequest):
    try:
        result = await extract_frames(
            video_url=req.video_url,
            frame_count=req.frame_count,
            quality=req.quality
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── APP 02: PROMPTGEN ────────────────────────────────────────────────────────

@app.post("/prompts")
async def app02_generate_prompts(req: PromptsOnlyRequest):
    try:
        result = await generate_prompts(
            frames_payload=req.frames_payload,
            anthropic_api_key=req.anthropic_api_key
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── APP 03: IMAGEGEN ─────────────────────────────────────────────────────────

@app.post("/images")
async def app03_generate_images(req: ImagesOnlyRequest):
    try:
        result = await generate_images(
            prompts_payload=req.prompts_payload,
            gemini_api_key=req.gemini_api_key
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── PIPELINE COMPLETO ────────────────────────────────────────────────────────

@app.post("/pipeline")
async def full_pipeline(req: PipelineRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id,
        "status": "running",
        "step": "starting",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
        "result": None,
        "error": None
    }
    background_tasks.add_task(run_pipeline, job_id, req)
    return {"job_id": job_id, "status": "started", "poll_url": f"/job/{job_id}"}


@app.get("/job/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return jobs[job_id]


async def run_pipeline(job_id: str, req: PipelineRequest):
    try:
        jobs[job_id].update({"step": "extracting_frames", "progress": 10})
        frames_payload = await extract_frames(
            video_url=req.video_url,
            frame_count=req.frame_count,
            quality=req.quality
        )
        jobs[job_id].update({"step": "frames_done", "progress": 35})

        jobs[job_id].update({"step": "generating_prompts", "progress": 40})
        prompts_payload = await generate_prompts(
            frames_payload=frames_payload,
            anthropic_api_key=req.anthropic_api_key
        )
        jobs[job_id].update({"step": "prompts_done", "progress": 65})

        jobs[job_id].update({"step": "generating_images", "progress": 70})
        images_payload = await generate_images(
            prompts_payload=prompts_payload,
            gemini_api_key=req.gemini_api_key
        )
        jobs[job_id].update({
            "step": "completed",
            "progress": 100,
            "status": "done",
            "result": {
                "frames": frames_payload,
                "prompts": prompts_payload,
                "images": images_payload
            }
        })

    except Exception as e:
        jobs[job_id].update({
            "status": "error",
            "error": str(e),
            "step": "failed"
        })
