# Takeoff Assistant API

FastAPI backend skeleton for the PDF drawing finish takeoff assistant MVP.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m uvicorn app.main:app --reload
```

The first implementation step is intentionally small: it only provides the app shell and `/health`.
