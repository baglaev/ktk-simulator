# КТК ЭЛОУ-АВТ

Компьютерный тренажёрный комплекс с учебной моделью сценария отказа сырьевого
насоса Н-1А, live-телеметрией через WebSocket и AI-модулем для итогового разбора
и послесессионного RAG.

Все численные траектории, пороги и временные окна сценария являются учебными
допущениями и не должны использоваться как производственные инструкции или
уставки оборудования.

## Состав проекта

- `frontend/` — пользовательский интерфейс тренажёра;
- `backend/` — FastAPI, модель сценария, WebSocket, REST API и база данных;
- `ai/` — детерминированный анализ, OpenRouter и локальный RAG;
- `run_backend_ai.sh` — единый запуск backend и AI.

AI не является отдельным сервером. Он подключается к backend как Python-модуль
и вызывается при формировании итогового анализа или ответа RAG.

## Первичная установка backend

Из корня репозитория:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env  # если backend/.env ещё не создан
cd ..
```

## Настройка AI

Создайте локальный файл настроек:

```bash
cp ai/.env.example ai/.env  # если ai/.env ещё не создан
```

Укажите в `ai/.env` ключ OpenRouter и модели:

```dotenv
AI_LLM_ENABLED=true
AI_LLM_BASE_URL=https://openrouter.ai/api/v1
AI_LLM_MODEL=google/gemma-4-26b-a4b-it:free
AI_LLM_FALLBACK_MODEL=openrouter/free
OPENROUTER_API_KEY=ваш-секретный-ключ
```

Файл `ai/.env` не добавляется в Git. Если основная модель недоступна, backend
один раз повторяет запрос через `openrouter/free`. Если не сработали обе модели,
система возвращает детерминированный анализ без LLM.

## Запуск backend и AI

Из корня репозитория выполните:

```bash
./run_backend_ai.sh
```

Скрипт:

1. загружает `ai/.env`;
2. проверяет ключ и настройки модели;
3. выполняет `alembic upgrade head`;
4. запускает FastAPI вместе с подключённым AI-модулем.

После запуска доступны:

- backend: <http://127.0.0.1:8000>;
- проверка состояния: <http://127.0.0.1:8000/health>;
- Swagger REST API: <http://127.0.0.1:8000/docs>;
- WebSocket: `ws://127.0.0.1:8000/ws/v1/sessions/{sessionId}`.

Остановка выполняется сочетанием `Ctrl+C`.

Другой порт или запуск без автоматической перезагрузки:

```bash
KTK_PORT=8001 KTK_RELOAD=false ./run_backend_ai.sh
```

## Запуск frontend

Во втором терминале:

```bash
cd frontend
npm install
npm run dev
```

Frontend обычно доступен по адресу <http://127.0.0.1:5173>.

## Проверка

Backend:

```bash
cd backend
source .venv/bin/activate
pytest -q
```

AI:

```bash
backend/.venv/bin/python -m pytest ai/tests -q
```

Подробные контракты REST и WebSocket описаны в
[backend/README.md](backend/README.md), устройство AI и RAG — в
[ai/README.md](ai/README.md).
