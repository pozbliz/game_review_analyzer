# Backend

Run from this directory after installing the development extras:

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m uvicorn game_review_analyzer.interfaces.http.app:app --reload
```
