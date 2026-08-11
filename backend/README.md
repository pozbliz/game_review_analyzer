# Backend

Install [uv](https://docs.astral.sh/uv/), then run from this directory:

```powershell
uv sync --locked --extra dev
uv run pytest
uv run uvicorn game_review_analyzer.interfaces.http.app:app --reload
```
