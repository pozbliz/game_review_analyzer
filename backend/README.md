# Backend

Install [uv](https://docs.astral.sh/uv/), then run from this directory:

```powershell
uv sync --locked --extra dev
uv run pytest
uv run uvicorn game_review_analyzer.interfaces.http.app:app --reload
```

The backend listens at `http://127.0.0.1:8000` by default.

During frontend development, open `http://localhost:5173`; Vite proxies API requests to this backend.
