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

## API сценариев

- `GET /api/v1/scenarios` - каталог доступных сценариев.
- `GET /api/v1/scenarios/MVP-SC-01/model-definition` - оборудование, связи,
  сигналы, источники и учебные допущения сценария Н-1А.
- `GET /docs` - интерактивная документация OpenAPI.

## Учебная модель Н-1А

Детерминированная модель находится в `app/simulation`. Траектории сигналов
заданы в `app/scenarios/data/n1a_model_profile.json`. Все коэффициенты,
временные точки и модельные значения имеют ссылки на учебные допущения.

Модель реализует `initialize`, `step`, `apply_action` и `get_snapshot`.
Одинаковая последовательность шагов и действий формирует одинаковый результат.

## API учебных сессий

- `POST /api/v1/sessions` - создать сессию.
- `POST /api/v1/sessions/{id}/start` - запустить модель.
- `POST /api/v1/sessions/{id}/pause` - приостановить сессию.
- `POST /api/v1/sessions/{id}/resume` - продолжить сессию.
- `POST /api/v1/sessions/{id}/complete` - завершить сессию.
- `GET /api/v1/sessions/{id}` - получить состояние сессии.
- `GET /api/v1/sessions/{id}/snapshot` - получить полный снимок модели.
- `POST /api/v1/sessions/{id}/actions` - передать учебное действие.
- `POST /api/v1/sessions/{id}/advance` - продвинуть виртуальное время;
  временный драйвер MVP до подключения WebSocket-цикла.

Активные сессии пока хранятся в памяти одного процесса и теряются при
перезапуске backend. Запуск нескольких worker потребует общего хранилища
состояния; это будет реализовано на следующем инфраструктурном этапе.

## Тесты

```bash
cd backend
pytest
```
