# ECOSYSTEM BACKEND
## Pipeline: TikTok URL → Frames → Prompts → Imagens

---

## ESTRUTURA

```
backend/
├── main.py                  ← API central (FastAPI)
├── services/
│   ├── frameshot.py         ← APP 01: extrai frames do TikTok
│   ├── promptgen.py         ← APP 02: gera prompts com Claude
│   └── imagegen.py          ← APP 03: gera imagens com Imagen 3
├── requirements.txt
├── Dockerfile
├── railway.toml
└── .env.example
```

---

## RODAR LOCALMENTE

### 1. Instalar dependências

```bash
# Instalar ffmpeg (necessário para yt-dlp)
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt install ffmpeg

# Instalar dependências Python
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite o .env com suas chaves
```

### 3. Iniciar o servidor

```bash
uvicorn main:app --reload --port 8000
```

### 4. Testar

Acesse: http://localhost:8000
Docs: http://localhost:8000/docs

---

## ENDPOINTS

### GET /health
Verifica se o servidor está online.

### POST /frames
Extrai frames de um vídeo TikTok.

```json
{
  "video_url": "https://www.tiktok.com/@user/video/123",
  "frame_count": 8,
  "quality": 90
}
```

### POST /prompts
Gera prompts a partir dos frames.

```json
{
  "frames_payload": { ... payload do /frames ... },
  "anthropic_api_key": "sk-ant-..."
}
```

### POST /images
Gera imagens a partir dos prompts.

```json
{
  "prompts_payload": { ... payload do /prompts ... },
  "gemini_api_key": "AIza..."
}
```

### POST /pipeline
Roda o pipeline completo em background.

```json
{
  "video_url": "https://www.tiktok.com/@user/video/123",
  "frame_count": 8,
  "quality": 90,
  "anthropic_api_key": "sk-ant-...",
  "gemini_api_key": "AIza..."
}
```
Retorna: `{ "job_id": "abc12345" }`

### GET /job/{job_id}
Acompanha o progresso do pipeline.

```json
{
  "id": "abc12345",
  "status": "running",
  "step": "generating_prompts",
  "progress": 40,
  "result": null
}
```

---

## DEPLOY NO RAILWAY

### 1. Instalar Railway CLI

```bash
npm install -g @railway/cli
railway login
```

### 2. Criar projeto

```bash
cd backend
railway init
railway up
```

### 3. Configurar variáveis no Railway

```
PORT=8000
```

### 4. URL do backend

Após o deploy, Railway fornece uma URL como:
`https://ecosystem-backend-production.up.railway.app`

Use essa URL no frontend para conectar os apps.

---

## FLUXO DO ECOSSISTEMA

```
                    URL TikTok
                        │
                   POST /frames
                        │
              frameshot_v1 payload
                        │
                   POST /prompts
                        │
              promptgen_v1 payload
                        │
                   POST /images
                        │
              imagegen_v1 payload
                        │
                  imagens 9:16 ✓

   OU tudo de uma vez:

        POST /pipeline → job_id
        GET  /job/{id} → polling até status: "done"
```

---

## CHAVES NECESSÁRIAS

| Chave | Onde obter | Uso |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com | APP 02 — gerar prompts |
| `GEMINI_API_KEY` | aistudio.google.com/apikey | APP 03 — gerar imagens |

---

## SEGURANÇA

- Nunca commitar as chaves no git
- O `.env` já está no `.gitignore`
- Em produção, use as variáveis de ambiente do Railway/Render
- As chaves são passadas por request (não ficam salvas no servidor)
