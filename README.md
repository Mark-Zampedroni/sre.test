# Math API - SRE Test Service

A simple FastAPI service for testing the SRE agent's error detection and remediation capabilities.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/add` | Add two numbers |
| POST | `/subtract` | Subtract b from a |
| POST | `/multiply` | Multiply two numbers |
| POST | `/divide` | Divide a by b |
| POST | `/power` | Raise a to the power of b |

## Request Format

```json
{
  "a": 10.5,
  "b": 3.2
}
```

## Response Format

```json
{
  "operation": "add",
  "a": 10.5,
  "b": 3.2,
  "result": 13.7
}
```

## Run Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Docker

```bash
docker build -t math-api .
docker run -p 8000:8000 math-api
```

## Test Requests

```bash
# Add
curl -X POST http://localhost:8000/add \
  -H "Content-Type: application/json" \
  -d '{"a": 10.5, "b": 3.2}'

# Divide
curl -X POST http://localhost:8000/divide \
  -H "Content-Type: application/json" \
  -d '{"a": 100, "b": 4}'
```
# Test PR
# Token test
