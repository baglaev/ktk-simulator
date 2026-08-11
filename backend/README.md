# Backend КТК ЭЛОУ-АВТ

Backend реализует учебный сценарий `MVP-SC-01`: live-модель отказа Н-1А,
двунаправленный WebSocket, действия обучаемого, журнал, автоматическое
завершение, результат SCR-04, объяснимый разбор SCR-05, план повторения и
послесессионный RAG.

Все численные траектории, пороги, критическая граница и нормативы времени
являются **учебными допущениями** `A-02`, `A-17`, `A-18`. Это не реальные
производственные уставки и не команды для промышленного оборудования.

## Стек

- Python, FastAPI, Pydantic;
- WebSocket;
- SQLAlchemy, Alembic;
- SQLite локально, PostgreSQL для развёртывания;
- pytest.

## Запуск

Backend и AI запускаются одним процессом: AI подключён к FastAPI как Python-модуль,
поэтому отдельный AI-сервер не требуется.

Первичная установка:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env  # только если .env ещё нет
cd ..
cp ai/.env.example ai/.env  # только если ai/.env ещё нет
```

Впишите `OPENROUTER_API_KEY` в `ai/.env`, затем из корня репозитория запускайте:

```bash
./run_backend_ai.sh
```

Скрипт загружает настройки AI, проверяет обязательные переменные, выполняет
`alembic upgrade head` и запускает Uvicorn. Модель и резервная модель задаются
только в `ai/.env`. Backend-настройки читает из `backend/.env`.

Необязательные настройки самого скрипта:

```bash
KTK_HOST=127.0.0.1 KTK_PORT=8001 KTK_RELOAD=false ./run_backend_ai.sh
```

Ручной эквивалент запуска:

```bash
set -a
source ai/.env
set +a
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

Проверка: <http://127.0.0.1:8000/health>. Swagger REST API:
<http://127.0.0.1:8000/docs>.

Alembic — не база данных, а система версий её структуры. Актуальная миграция:
`20260811_02 (head)`. После `git pull` снова выполняйте `alembic upgrade head`.

SQLite используется по умолчанию:

```dotenv
KTK_DATABASE_URL=sqlite+pysqlite:///./ktk_simulator.sqlite3
```

Для PostgreSQL:

```dotenv
KTK_DATABASE_URL=postgresql+psycopg://ktk:ktk@localhost:5432/ktk_simulator
```

Если порт занят, найдите старый процесс командой
`lsof -nP -iTCP:8000 -sTCP:LISTEN` и остановите соответствующий Uvicorn.

## Вход

`POST /api/v1/auth/login` принимает `login` и `password`.

Обучаемый: `user` / `user`. Инструктор: `instructor` / `instructor`.

Успешный ответ:

```json
{"login": true, "role": "user", "redirectTo": "/"}
```

или:

```json
{"login": true, "role": "instructor", "redirectTo": "/instructor"}
```

Ошибка возвращает HTTP 401:

```json
{"login": false, "error": "Неверный логин или пароль"}
```

Frontend сам выполняет переход на `redirectTo`. Это демонстрационная
аутентификация без JWT и защиты остальных маршрутов; для production она не
подходит.

### Учебные корпоративные учётные записи

Дополнительно доступны 20 корпоративно оформленных demo-аккаунтов. Все они
имеют роль `user` и после успешного входа возвращают `redirectTo: "/"`.

| Логин | Пароль |
|---|---|
| `Matveev.AD@gazprom-neft.ru` | `GpnDemo#Mat26` |
| `Voronov.NK@gazprom-neft.ru` | `GpnDemo#Vor26` |
| `Sokolov.IV@gazprom-neft.ru` | `GpnDemo#Sok26` |
| `Kuznetsov.MA@gazprom-neft.ru` | `GpnDemo#Kuz26` |
| `Popov.ES@gazprom-neft.ru` | `GpnDemo#Pop26` |
| `Smirnova.OV@gazprom-neft.ru` | `GpnDemo#Smi26` |
| `Petrova.AN@gazprom-neft.ru` | `GpnDemo#Pet26` |
| `Volkov.DS@gazprom-neft.ru` | `GpnDemo#Vol26` |
| `Fedorov.PM@gazprom-neft.ru` | `GpnDemo#Fed26` |
| `Morozova.EV@gazprom-neft.ru` | `GpnDemo#Mor26` |
| `Lebedev.RA@gazprom-neft.ru` | `GpnDemo#Leb26` |
| `Novikova.TS@gazprom-neft.ru` | `GpnDemo#Nov26` |
| `Orlov.KV@gazprom-neft.ru` | `GpnDemo#Orl26` |
| `Pavlov.SI@gazprom-neft.ru` | `GpnDemo#Pav26` |
| `Semenova.NA@gazprom-neft.ru` | `GpnDemo#Sem26` |
| `Golubev.VP@gazprom-neft.ru` | `GpnDemo#Gol26` |
| `Vinogradova.MI@gazprom-neft.ru` | `GpnDemo#Vin26` |
| `Bogdanov.AL@gazprom-neft.ru` | `GpnDemo#Bog26` |
| `Komarova.ER@gazprom-neft.ru` | `GpnDemo#Kom26` |
| `Zakharov.DN@gazprom-neft.ru` | `GpnDemo#Zak26` |

Пароли содержат не менее 12 символов. Фамилии и инициалы являются синтетическим
demo-набором; весь список предназначен только для демонстрации. Это не
подключение к корпоративному AD/SSO, и такие учётные данные нельзя использовать
в production.

## Жизненный цикл сценария

1. `GET /api/v1/scenarios/MVP-SC-01/model-definition` — получить оборудование,
   сигналы, форму диагностики и происхождение данных.
2. `POST /api/v1/sessions` — создать сессию и выбрать `training` или `control`.
3. Взять `sessionId` из ответа.
4. `POST /api/v1/sessions/{sessionId}/start` — запустить live-модель.
5. Открыть `ws://127.0.0.1:8000/ws/v1/sessions/{sessionId}`.
6. Применить первый `telemetry.snapshot`, затем `telemetry.update`.
7. Передавать действия обучаемого через этот же WebSocket.
8. Дождаться `scenarioState.status = completed`.
9. Получить `GET .../result`, создать `POST .../ai-analysis`, затем запросить
   `GET .../adaptive-plan`.

Backend автоматически продвигает виртуальное время раз в секунду. `/advance`
нужен только тестам и ручной отладке.

Максимальное учебное время попытки — 180 секунд. Без корректирующих действий
траектория достигает учебной границы LRCA 605 = 20% на 120-й секунде и попытка
завершается раньше как неуспешная. Восстановление, начатое до критической
границы, длится 30 учебных секунд и может завершиться после 120-й секунды, но до
180-й. Это учебное допущение, а не производственный норматив.

Успешная стабилизация и критическая граница завершают сессию автоматически.
`POST .../complete` оставлен только для досрочного ручного завершения; такая
попытка оценивается как `failed`.

## REST API

| Метод | URL | Назначение |
|---|---|---|
| GET | `/api/v1/scenarios` | каталог сценариев |
| GET | `/api/v1/scenarios/MVP-SC-01/model-definition` | статическая модель и форма диагностики |
| POST | `/api/v1/sessions` | создать сессию |
| GET | `/api/v1/sessions/{id}` | состояние сессии |
| POST | `/api/v1/sessions/{id}/start` | запуск |
| POST | `/api/v1/sessions/{id}/pause` | пауза |
| POST | `/api/v1/sessions/{id}/resume` | продолжение |
| POST | `/api/v1/sessions/{id}/complete` | досрочно завершить как неуспешную |
| GET | `/api/v1/sessions/{id}/snapshot` | полный текущий снимок |
| GET | `/api/v1/sessions/{id}/actions` | журнал принятых действий |
| GET | `/api/v1/sessions/{id}/hints` | реально показанные подсказки |
| GET | `/api/v1/sessions/{id}/result` | детерминированный SCR-04 |
| POST | `/api/v1/sessions/{id}/ai-analysis` | создать и сохранить SCR-05 |
| GET | `/api/v1/sessions/{id}/ai-analysis` | получить созданный SCR-05 |
| GET | `/api/v1/sessions/{id}/adaptive-plan` | план повторной отработки |
| POST | `/api/v1/sessions/{id}/assistant/question` | RAG-вопрос после завершения |
| POST | `/api/v1/sessions/{id}/advance` | только ручной тестовый шаг времени |

Создание сессии:

```json
{
  "scenarioId": "MVP-SC-01",
  "traineeId": "trainee-001",
  "instructorId": "instructor-001",
  "mode": "training"
}
```

`training` включает подготовленные подсказки. `control` соответствует
экзаменационному режиму и никогда не отправляет подсказки.

## WebSocket

WebSocket отсутствует в Swagger, потому что OpenAPI описывает HTTP, а не WS.
Один канал двунаправленный:

```text
frontend → backend: действия пользователя
backend → frontend: action.result, telemetry.*, scenario.hint
```

Frontend отправляет только минимальный JSON. Backend сам добавляет `sessionId`,
UUID действия, серверное время, версию состояния и ключ идемпотентности.

```json
{"actionType": "view_signal", "targetId": "PRA351"}
```

Основные действия сценария:

| `actionType` | `targetId` | `parameters` |
|---|---|---|
| `open_equipment_card` | оборудование, например `eq-n1a` | нет |
| `view_signal` | сигнал, например `PRA351` | нет |
| `run_diagnostics` | только `eq-n1a` | нет |
| `submit_diagnosis` | `eq-n1a` | `conclusion`, иногда `reason` |
| `start_pump` | учебный насос, например `eq-n1b` | нет |
| `stop_pump` | учебный насос, например `eq-n1a` | нет |

`submit_decision` и `acknowledge_event` зарезервированы контрактом, но текущий
MVP не требует их для успешного пути.

### Форма диагностики

Источник вариантов для frontend — поле `diagnosisForm` в model-definition.
Правильный ответ там намеренно не раскрывается.

Открытие формы:

```json
{"actionType": "run_diagnostics", "targetId": "eq-n1a"}
```

Выявлена неисправность — `reason` обязателен:

```json
{
  "actionType": "submit_diagnosis",
  "targetId": "eq-n1a",
  "parameters": {
    "conclusion": "fault_detected",
    "reason": "bearing_wear"
  }
}
```

Допустимые причины: `bearing_wear`, `cavitation`, `electrical_overload`,
`suction_supply_disruption`, `compax_sensor_fault`.

Неисправность не выявлена — `reason` не передаётся:

```json
{
  "actionType": "submit_diagnosis",
  "targetId": "eq-n1a",
  "parameters": {"conclusion": "no_fault"}
}
```

Значения `0`/`1` не используются: строковые коды устойчивее, понятнее в
журнале и не требуют помнить смысл числа.

### Сообщения backend

При подключении приходит полный `telemetry.snapshot`, далее — полные списки тех
же восьми компонентов в `telemetry.update`. В каждом сообщении есть:

- `sequenceNo` — порядок сообщений модели;
- `stateVersion` — версия состояния;
- `mode` — `training` или `control`;
- `timing` — live-время, максимум и прогресс;
- `scenarioState.status` — `active` или `completed`;
- `scenarioState.completionReason` — причина автоматического завершения;
- `components` — неизменный по составу список компонентов;
- `journal` — записи формата «время — описание действия».

Параметр компонента:

```json
{
  "parameterId": "COMPAX.N1A.VELOCITY",
  "measurementType": "vibration_velocity",
  "value": 7.9,
  "unit": "мм/с",
  "status": "alert"
}
```

COMPAX передаётся в физических единицах: °C, мм/с, м/с², мкм; ток — в процентах
от учебной базовой величины. PRA 351, FYQR 117, ЭЛОУ и LRCA 605 остаются в `%`,
потому что подтверждённых абсолютных режимных траекторий нет. Поле
`valuePercent` удалено.

Подсказка приходит отдельным сообщением, поэтому обработчик frontend должен
ветвиться по `type`, а не считать каждое сообщение телеметрией:

```json
{
  "type": "scenario.hint",
  "sessionId": "...",
  "virtualTimeMs": 10000,
  "hintId": "inspect-n1a",
  "level": "warning",
  "title": "Проверьте Н-1А",
  "message": "Статус Н-1А изменился...",
  "displayDurationMs": 8000,
  "provenance": {
    "method": "deterministic_rule",
    "llmUsed": false,
    "sourceRefs": ["A-18", "учебное допущение"]
  }
}
```

`displayDurationMs` позволяет показать временный popup. Во время live-сценария
нейросеть и внешний API не вызываются.

Пример маршрутизации сообщений:

```javascript
socket.onmessage = ({ data }) => {
  const message = JSON.parse(data);
  if (message.type === "telemetry.snapshot" || message.type === "telemetry.update") {
    renderTelemetry(message);
  } else if (message.type === "action.result") {
    handleActionResult(message);
  } else if (message.type === "scenario.hint") {
    showTemporaryHint(message, message.displayDurationMs);
  }
};
```

## Результат и ИИ

SCR-04 рассчитывается кодом и содержит статус `passed`,
`passed_with_remarks` или `failed`, балл 0–100, выполнение задач, конечные и
минимальные контролируемые параметры, замечания и причину завершения.

SCR-05 создаётся после результата. Он содержит упорядоченные карточки ошибок:
классификацию, время, действие пользователя, последствие, правильный учебный
подход, прогноз повторения и время показанной подсказки. SCR-05 не меняет балл
и статус SCR-04 (`scoreChanged: false`).

Если загружен `OPENROUTER_API_KEY`, один LLM-вызов может улучшить только текст
итогового SCR-05. Коды ошибок, их порядок, балл и статус проверяются и остаются
детерминированными. Без ключа возвращается полноценный шаблонный разбор с
`llmUsed: false`.

RAG доступен только после завершения сессии, поэтому он не подсказывает ответ во
время экзамена. Запрос:

```json
{"question": "Почему в учебной модели анализируют PRA 351?"}
```

Перед использованием постройте локальный индекс из корня репозитория:

```bash
python3 -m ai.examples.build_rag_index \
  --source-dir "/полный/путь/КТК_ЭЛОУ_АВТ_пакет_для_промта"
```

Без индекса endpoint вернёт HTTP 503. Без ключа OpenRouter RAG безопасно
возвращает найденные источники и fallback; секретный ключ никогда не уходит во
frontend.

## Таблицы БД

- `training_sessions` — сессии и их статусы;
- `operator_actions` — аудит действий;
- `session_results` — SCR-04 целиком в JSON;
- `issued_hints` — реально показанные live-подсказки;
- `session_ai_analyses` — сохранённый SCR-05;
- `alembic_version` — версия структуры БД.

## Проверка

```bash
cd backend
source .venv/bin/activate
pytest -q
cd ..
backend/.venv/bin/python -m pytest ai/tests -q
```
