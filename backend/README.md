# Backend КТК

## Стек технологий

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- WebSocket

## Запуск каркаса

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Проверка: <http://127.0.0.1:8000/health>

## Тесты

```bash
cd backend
pytest
```
