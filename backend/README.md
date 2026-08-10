# Backend КТК ЭЛОУ-АВТ

Версия backend `0.3.0` реализует полный учебный путь MVP по развивающейся
неисправности сырьевого насоса Н-1А: live-модель, действия обучаемого,
переключение Н-1А → Н-1Б, восстановление параметров, журнал, результат и БД.

Все временные точки, пороги и численные траектории сценария являются
**учебными допущениями** и не являются производственными инструкциями или
уставками. В `model-definition` правила восстановления отмечены `A-17`, а
пороги статусов и шкала оценки — `A-18`.

## Стек

- Python, FastAPI, Pydantic;
- WebSocket;
- SQLAlchemy, Alembic;
- PostgreSQL; SQLite используется как локальный fallback;
- pytest.

## Запуск

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

В `.env` выберите БД:

```dotenv
# целевой вариант
KTK_DATABASE_URL=postgresql+psycopg://ktk:ktk@localhost:5432/ktk_simulator

# локальный вариант без PostgreSQL
KTK_DATABASE_URL=sqlite+pysqlite:///./ktk_simulator.sqlite3
```

Для PostgreSQL перед запуском примените миграцию:

```bash
alembic upgrade head
```

Проверка backend: <http://127.0.0.1:8000/health>. Swagger REST API:
<http://127.0.0.1:8000/docs>.

## Что реализовано

- на 10-й секунде Н-1А переходит в `warning`;
- диагностика Н-1А с выводом и причиной;
- команды запуска/останова четырёх учебных насосов;
- Н-1Б изначально остановлен, Н-1, Н-1А и Н-1В работают;
- безопасная конфигурация: Н-1Б работает, Н-1А остановлен, Н-1 и Н-1В
  работают;
- после безопасного переключения начинается линейное восстановление 30 секунд:
  PRA 351, FYQR 117 и уровни ЭЛОУ до 100%, LRCA 605 до исходных 65%;
- при достижении LRCA 605 значения 20% без запущенного восстановления сценарий
  автоматически завершается как `failed`;
- неверная диагностика уменьшает баллы, но не изменяет физическую динамику;
- детерминированная оценка 0–100 с ошибками, штрафами и критическими условиями;
- постоянный аудит сессий, действий и результатов в БД.

## REST API

- `GET /api/v1/scenarios` — каталог сценариев;
- `GET /api/v1/scenarios/MVP-SC-01/model-definition` — статическая модель,
  источники и учебные допущения;
- `POST /api/v1/sessions` — создать сессию;
- `POST /api/v1/sessions/{id}/start` — запустить live-модель;
- `POST /api/v1/sessions/{id}/pause` / `resume` — пауза / продолжение;
- `POST /api/v1/sessions/{id}/actions` — действие обучаемого;
- `GET /api/v1/sessions/{id}/actions` — сохранённый аудит действий;
- `GET /api/v1/sessions/{id}/snapshot` — текущий полный снимок;
- `POST /api/v1/sessions/{id}/complete` — завершить прохождение;
- `GET /api/v1/sessions/{id}/result` — результат SCR-04;
- `POST /api/v1/sessions/{id}/advance` — только тестовый ручной шаг времени.

Frontend не вызывает `/advance`: в обычном запуске время продвигает backend.

## WebSocket

Адрес: `WS /ws/v1/sessions/{sessionId}`.

Первое сообщение — `telemetry.snapshot`, последующие — `telemetry.update`.
Каждое сообщение содержит полный упорядоченный массив восьми компонентов,
вложенные параметры, live-время и журнал вида `time` / `description`.

Команды пользователя идут через REST `/actions`. WebSocket используется в
обратном направлении — для отправки актуального состояния backend → frontend.
WebSocket-маршрут не отображается в Swagger/OpenAPI; полный контракт находится
в [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md).

Матрица требований и автотестов: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

## Состояние и хранение

Активный расчёт модели живёт в памяти одного процесса FastAPI, поэтому MVP
запускается с одним worker. Метаданные сессий, все принятые действия и результаты
сохраняются в БД и доступны для последующего AI-анализа. После перезапуска можно
читать архив и результат, но продолжить незавершённый live-расчёт нельзя.

Redis/Kafka не требуются для одного worker. Внешний брокер понадобится при
горизонтальном масштабировании и нескольких экземплярах backend.

## Тесты

```bash
cd backend
KTK_DATABASE_URL=sqlite+pysqlite:///:memory: pytest
```
