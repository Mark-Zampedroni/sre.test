# 🖼️ ImageForge

**Retro Image Processing Lab** — An image processing web application.

## Features

- **Upload** images (JPEG, PNG, WebP, GIF)
- **Transform**: resize, rotate, crop, grayscale, blur, invert, sepia, sharpen, edge detection
- **Download** processed results
- **Retro CRT-style UI** with scanlines and glow effects

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/stats` | GET | Service statistics |
| `/api/upload` | POST | Upload image |
| `/api/transform/{id}` | POST | Transform image |
| `/api/image/{id}` | GET | Download image |
| `/api/history` | GET | Recent jobs |

## Run Locally

```bash
docker build -t imageforge .
docker run -p 8000:8000 imageforge
```

Then open http://localhost:8000
