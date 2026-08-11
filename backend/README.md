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
| GET | `/api/v1/sessions/{id}/ai-analysis/report.pdf` | скачать созданный SCR-05 как PDF |
| GET | `/api/v1/sessions/{id}/adaptive-plan` | план повторной отработки |
| POST | `/api/v1/sessions/{id}/assistant/question` | RAG-вопрос после завершения |
| POST | `/api/v1/sessions/{id}/advance` | только ручной тестовый шаг времени |
| GET | `/api/v1/instructor/overview` | сводные показатели инструктора |
| GET | `/api/v1/instructor/trainees` | полный список назначенных обучаемых |
| GET | `/api/v1/instructor/trainees/{traineeId}` | карточка обучаемого |
| GET | `/api/v1/instructor/trainees/{traineeId}/results` | попытки обучаемого |
| GET | `/api/v1/instructor/trainees/{traineeId}/results/{sessionId}` | полный результат попытки |
| GET | `/api/v1/instructor/trainees/{traineeId}/results/{sessionId}/journal` | журнал действий и подсказок |
| GET | `/api/v1/instructor/results` | список завершённых результатов обучаемых |

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

### Результаты для страницы инструктора

При открытии страницы frontend сначала запрашивает:

```http
GET /api/v1/instructor/overview
GET /api/v1/instructor/trainees
```

`/trainees` сразу возвращает всех назначенных обучаемых: базового `user`, 20
синтетических корпоративных демо-учёток и дополнительные идентификаторы,
обнаруженные в сохранённой истории. Для текущего MVP используется один
инструктор, поэтому все демо-обучаемые по умолчанию назначены `instructor`.
Пароли API никогда не возвращает.

У каждого обучаемого есть агрегаты и `latestResult`. Если попыток ещё не было,
`attemptsCount` равен `0`, а `latestResult` равен `null`. После прохождения
`latestResult` содержит `sessionId`, режим, статус, балл и время завершения:

```json
{
  "traineeId": "Matveev.AD@gazprom-neft.ru",
  "login": "Matveev.AD@gazprom-neft.ru",
  "fullName": "Матвеев Александр Дмитриевич",
  "assignedInstructorId": "instructor",
  "accountSource": "demo_directory",
  "attemptsCount": 1,
  "successfulAttemptsCount": 1,
  "averageScore": 92,
  "bestScore": 92,
  "lastCompletedAt": "2026-08-11T12:00:00Z",
  "latestResult": {
    "sessionId": "f3656f3b-3b2c-44e5-9cb8-46b50ad6f715",
    "traineeId": "Matveev.AD@gazprom-neft.ru",
    "instructorId": "instructor",
    "scenarioId": "MVP-SC-01",
    "scenarioVersion": "0.4.0",
    "mode": "training",
    "sessionStatus": "completed",
    "resultStatus": "passed",
    "outcome": "success",
    "totalScore": 92,
    "maxScore": 100,
    "elapsedTimeMs": 87000,
    "completedAt": "2026-08-11T12:00:00Z"
  }
}
```

История выбранного обучаемого:

```http
GET /api/v1/instructor/trainees/{traineeId}/results
```

Поддерживает `mode`, `limit` и `offset`. Полный результат и журнал выбранной
попытки frontend получает отдельно:

```http
GET /api/v1/instructor/trainees/{traineeId}/results/{sessionId}
GET /api/v1/instructor/trainees/{traineeId}/results/{sessionId}/journal
```

Журнал имеет стабильный формат «время — описание» и содержит принятые действия
обучаемого, а в режиме `training` также реально показанные подсказки:

```json
{
  "sessionId": "f3656f3b-3b2c-44e5-9cb8-46b50ad6f715",
  "traineeId": "Matveev.AD@gazprom-neft.ru",
  "mode": "training",
  "items": [
    {
      "time": "00:31",
      "virtualTimeMs": 31000,
      "kind": "action",
      "description": "Просмотрен сигнал PRA 351"
    }
  ]
}
```

Общий список всех завершённых попыток доступен одним запросом без параметров:

```http
GET /api/v1/instructor/results
```

Пример ответа:

```json
{
  "items": [
    {
      "sessionId": "f3656f3b-3b2c-44e5-9cb8-46b50ad6f715",
      "traineeId": "trainee-001",
      "traineeName": "trainee-001",
      "instructorId": "instructor-001",
      "scenarioId": "MVP-SC-01",
      "scenarioVersion": "0.4.0",
      "mode": "training",
      "sessionStatus": "completed",
      "resultStatus": "passed",
      "outcome": "success",
      "totalScore": 92,
      "maxScore": 100,
      "elapsedTimeMs": 87000,
      "completedAt": "2026-08-11T12:00:00Z",
      "journal": [
        {
          "time": "00:31",
          "virtualTimeMs": 31000,
          "kind": "action",
          "description": "Просмотрен параметр PRA 351"
        }
      ]
    }
  ],
  "total": 1
}
```

Незавершённые сессии в результаты не входят, но сам обучаемый остаётся в полном
списке `/trainees`.

Текущая авторизация демонстрационная и не выдаёт токен, поэтому эта ручка пока
не проверяет роль вызывающего пользователя. Перед промышленным использованием
нужно добавить токен и серверную проверку роли `instructor`.

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

Каждая выданная учебная подсказка одновременно приходит отдельным сообщением
`scenario.hint` для временного popup и добавляется в `journal` как запись
`Подсказка «заголовок»: текст`. Поэтому она остаётся в истории после закрытия
popup и повторного подключения к сессии. В режиме `control` таких сообщений и
записей нет.

Параметр компонента:

```json
{
  "parameterId": "COMPAX.N1A.VELOCITY",
  "measurementType": "vibration_velocity",
  "value": 8,
  "unit": "мм/с",
  "status": "alert"
}
```

COMPAX передаётся в физических единицах: °C, мм/с, м/с², мкм; ток — в процентах
от учебной базовой величины. PRA 351, FYQR 117, ЭЛОУ и LRCA 605 остаются в `%`,
потому что подтверждённых абсолютных режимных траекторий нет. Поле
`valuePercent` удалено. Все динамические `value`, `progressPercent`,
`faultSeverityPercent`, а также `finalValue` и `minimumValue` в результате
передаются целыми числами. Внутри модели расчёт остаётся дробным, округление
`0.5` выполняется вверх только при формировании внешнего контракта. Паспортные
значения в `model-definition` не округляются, чтобы не искажать исходные данные.

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

### Инструкция для frontend: журнал и подсказки

Frontend создаёт сессию с выбранным режимом, запускает её и только после этого
открывает WebSocket:

```text
POST /api/v1/sessions с mode = training | control
→ POST /api/v1/sessions/{sessionId}/start
→ ws://127.0.0.1:8000/ws/v1/sessions/{sessionId}
```

Если подключиться к ещё не запущенной сессии, backend закроет соединение с
кодом `4409`. Для неизвестного `sessionId` используется код `4404`, для
запрещённого `Origin` — `4403`.

Первое WS-сообщение — `telemetry.snapshot`. После него приходят
`telemetry.update`. Поле `journal` в обоих типах содержит **полный текущий
журнал**, а не только новые записи:

```json
{
  "journal": [
    {
      "entryId": "9d04a728-0000-0000-0000-000000000000",
      "time": "00:10",
      "description": "Подсказка «Проверьте Н-1А»: Статус Н-1А изменился..."
    }
  ]
}
```

Поэтому frontend должен заменять массив целиком:

```javascript
function applyTelemetry(message) {
  if (
    message.type === "telemetry.update" &&
    message.sequenceNo <= lastSequenceNo
  ) {
    return;
  }

  lastSequenceNo = message.sequenceNo;
  components = message.components;
  journal = message.journal; // заменить, не append/push
  timing = message.timing;
  scenarioState = message.scenarioState;
}
```

В журнал автоматически попадают события модели, принятые действия пользователя,
завершение сценария и выданные подсказки. Отклонённое действие в журнал не
добавляется. Для действия `entryId` совпадает с серверным `actionId`.

В режиме `training` backend проверяет правила после каждого тика модели и после
каждого принятого действия. Подсказка может появиться, когда:

- Н-1А перешёл в `warning`/`alert`, но его карточка не открыта;
- карточка Н-1А открыта, но PRA 351 и FYQR 117 ещё не сопоставлены;
- оба линейных сигнала просмотрены, но диагностика не запущена;
- диагностика запущена, но заключение не отправлено;
- правильный диагноз указан, но безопасная учебная конфигурация насосов не
  достигнута;
- началось восстановление параметров;
- Н-1А и Н-1Б одновременно остановлены;
- сценарий завершился.

Каждый `hintId` выдаётся не более одного раза за сессию; за одно обновление
формируется максимум одна подсказка. В режиме `control` сообщения
`scenario.hint` и соответствующие записи в журнале отсутствуют.

Если правило сработало, backend сначала добавляет текст подсказки в журнал,
затем отправляет два сообщения:

```text
telemetry.update с обновлённым полным journal
→ scenario.hint для временного popup
```

После действия пользователя порядок такой:

```text
action.result
→ telemetry.update с записью действия и, возможно, подсказки
→ scenario.hint, если сработало новое правило
```

`scenario.hint` не нужно вручную добавлять в журнал — это создаст дубликат.
Frontend использует его только для popup и закрывает popup через
`displayDurationMs`. При переподключении предыдущие popup не повторяются, но их
записи остаются в полном `journal` начального `telemetry.snapshot`.

Рекомендуемая маршрутизация:

```javascript
socket.onmessage = ({ data }) => {
  const message = JSON.parse(data);

  switch (message.type) {
    case "telemetry.snapshot":
    case "telemetry.update":
      applyTelemetry(message);
      break;
    case "scenario.hint":
      showTemporaryHint(message, message.displayDurationMs);
      break;
    case "action.result":
      handleActionResult(message);
      break;
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

Перед единственным постсценарным LLM-вызовом backend формирует обезличенный
контекст: полный доступный журнал сессии, хронологию принятых действий, этапы и
время реакции, порядок диагностики и переключения, фактически показанные
подсказки, карточки ошибок, выполнение задач, причину завершения, минимальные и
конечные контролируемые параметры. `sessionId`, `traineeId` и `instructorId` во
внешний LLM не отправляются. После перезапуска backend, когда live-модель уже не
находится в памяти, отчёт всё равно строится по сохранённым результату, действиям
и подсказкам.

Расширенный контекст является внутренней реализацией. Контракт
`SessionAIAnalysis` не изменяется, поэтому frontend продолжает использовать те
же поля `summary`, `strengths`, `errors`, `recommendations` и `provenance`.

После `POST .../ai-analysis` тот же отчёт можно скачать как PDF:

```bash
curl -o ktk-ai-report.pdf \
  http://127.0.0.1:8000/api/v1/sessions/{sessionId}/ai-analysis/report.pdf
```

Ответ имеет `Content-Type: application/pdf` и `Content-Disposition: attachment`.
PDF содержит итог и балл, общий вывод, сильные стороны, карточки ошибок,
рекомендации, информацию об использовании LLM и учебный дисклеймер. Если JSON
анализ ещё не был сформирован, endpoint возвращает `409`; сначала нужно вызвать
`POST .../ai-analysis`. Существующий JSON-контракт не меняется, поэтому кнопка
скачивания PDF является для frontend дополнительной необязательной функцией.

Для кириллицы генератор автоматически ищет DejaVu Sans или Liberation Sans в
Linux, Arial в macOS/Windows. В минимальном окружении путь можно задать явно:

```dotenv
PDF_FONT_PATH=/path/to/Unicode-Regular.ttf
PDF_FONT_BOLD_PATH=/path/to/Unicode-Bold.ttf
```

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
