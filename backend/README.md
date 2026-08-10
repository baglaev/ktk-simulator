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

## Быстрый локальный запуск

Команды выполняются из корня репозитория. Для локальной разработки по
умолчанию достаточно SQLite: отдельный сервер БД устанавливать не нужно.

### 1. Подготовить окружение

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Если файла `.env` ещё нет, создайте его из примера:

```bash
cp .env.example .env
```

В `.env` выберите подключение к БД. Для локального запуска:

```dotenv
KTK_DATABASE_URL=sqlite+pysqlite:///./ktk_simulator.sqlite3
```

### 2. Подготовить структуру БД

Alembic — не база данных, а инструмент управления версиями структуры БД.
Команда ниже создаёт недостающие таблицы и применяет новые миграции к выбранной
в `.env` SQLite или PostgreSQL:

```bash
alembic upgrade head
```

Проверить применённую версию можно командой:

```bash
alembic current
```

Текущая версия должна содержать `20260810_01 (head)`. Миграцию следует
выполнять после каждого `git pull`, если в проекте появились новые файлы
миграций. Версия `20260810_01` умеет принять локальные таблицы, созданные
ранней версией backend до внедрения Alembic; удалять БД или выполнять
`alembic stamp` вручную не нужно.

### 3. Запустить backend

```bash
uvicorn app.main:app --reload
```

Проверка backend: <http://127.0.0.1:8000/health>. Swagger REST API:
<http://127.0.0.1:8000/docs>.

Остановить backend можно сочетанием `Ctrl+C` в терминале, где запущен Uvicorn.

## Запуск с PostgreSQL

Создайте БД и пользователя PostgreSQL, затем укажите подключение в `.env`:

```dotenv
KTK_DATABASE_URL=postgresql+psycopg://ktk:ktk@localhost:5432/ktk_simulator
```

После этого примените миграции и запустите backend:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload
```

## Частые ошибки запуска

### `Address already in use`

Порт `8000` уже занят, чаще всего ранее запущенным Uvicorn. Найдите процесс:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Если это старый процесс Uvicorn, остановите его в исходном терминале через
`Ctrl+C` или выполните `kill <PID>`, подставив PID из вывода `lsof`.

### `table training_sessions already exists`

Сначала получите актуальную версию ветки и повторно примените миграцию:

```bash
git pull
cd backend
source .venv/bin/activate
alembic upgrade head
```

Актуальная миграция принимает уже существующую схему. Удалять локальную БД и
вручную помечать миграцию применённой не требуется.

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

## Интеграция frontend и backend

Для обмена используются два механизма:

| Механизм | Назначение |
|---|---|
| REST API | описание модели, создание, запуск, пауза, завершение сессии и результат |
| WebSocket | действия пользователя во время сценария и live-телеметрия |

Адреса локального backend:

- REST: `http://127.0.0.1:8000`;
- Swagger REST API: `http://127.0.0.1:8000/docs`;
- WebSocket: `ws://127.0.0.1:8000/ws/v1/sessions/{sessionId}`.

WebSocket не входит в OpenAPI и поэтому не отображается в Swagger. Его полный
контракт описан ниже.

### Последовательность работы frontend

1. Получить модель: `GET /api/v1/scenarios/MVP-SC-01/model-definition`.
2. Создать сессию: `POST /api/v1/sessions`.
3. Сохранить `sessionId` из ответа.
4. Запустить сессию: `POST /api/v1/sessions/{sessionId}/start`.
5. Подключиться к WebSocket с полученным `sessionId`.
6. Применить первое сообщение `telemetry.snapshot`.
7. Отправлять действия кнопок минимальными JSON-сообщениями в WebSocket.
8. Обрабатывать подтверждения `action.result`.
9. Обновлять экран из сообщений `telemetry.update`.
10. После `ready_to_complete` вызвать REST `/complete` и `/result`.

### REST API

- `GET /api/v1/scenarios` — каталог сценариев;
- `GET /api/v1/scenarios/MVP-SC-01/model-definition` — статическая модель,
  источники и учебные допущения;
- `POST /api/v1/sessions` — создать сессию;
- `GET /api/v1/sessions/{id}` — получить состояние сессии;
- `POST /api/v1/sessions/{id}/start` — запустить live-модель;
- `POST /api/v1/sessions/{id}/pause` — поставить сессию на паузу;
- `POST /api/v1/sessions/{id}/resume` — продолжить сессию;
- `GET /api/v1/sessions/{id}/snapshot` — получить полный снимок;
- `POST /api/v1/sessions/{id}/complete` — завершить прохождение;
- `GET /api/v1/sessions/{id}/result` — получить результат SCR-04;
- `GET /api/v1/sessions/{id}/actions` — получить сохранённый аудит действий;
- `POST /api/v1/sessions/{id}/advance` — тестовый ручной шаг времени.

Frontend не отправляет действия пользователя через REST и не вызывает
`/advance` в обычном live-режиме: время продвигает backend.

Тело создания сессии:

```json
{
  "scenarioId": "MVP-SC-01",
  "traineeId": "trainee-001",
  "instructorId": "instructor-001",
  "mode": "training"
}
```

## WebSocket-контракт

Соединение открывается после запуска сессии:

```text
ws://127.0.0.1:8000/ws/v1/sessions/{sessionId}
```

Один WebSocket двунаправленный:

```text
frontend → backend: действия пользователя
backend → frontend: action.result и телеметрия
```

### Что frontend отправляет в backend

Действие передаётся текстовым JSON-сообщением. Минимальный пример:

```json
{
  "actionType": "view_signal",
  "targetId": "PRA351"
}
```

Допустимые поля:

| Поле | Обязательность | Назначение |
|---|---|---|
| `actionType` | всегда | тип действия из списка ниже |
| `targetId` | для действия над объектом | идентификатор компонента, сигнала или события |
| `parameters` | когда действию нужны данные | дополнительные значения, например диагноз |

Frontend не передаёт `actionId`, `sessionId`, `submittedAt`,
`expectedStateVersion` и `idempotencyKey`. Backend получает `sessionId` из URL,
сам создаёт UUID и серверное время, использует текущую версию состояния и
сохраняет полную запись действия в БД.

Пример отправки из frontend:

```javascript
const socket = new WebSocket(
  `ws://127.0.0.1:8000/ws/v1/sessions/${sessionId}`
);

function sendScenarioAction(actionType, targetId, parameters) {
  if (socket.readyState !== WebSocket.OPEN) return;

  const message = { actionType };
  if (targetId !== undefined) message.targetId = targetId;
  if (parameters !== undefined) message.parameters = parameters;

  socket.send(JSON.stringify(message));
}
```

### Доступные действия

Единственный программный источник списка — `ActionType` в
`app/domain/enums.py`.

| `actionType` | Назначение | Пример `targetId` |
|---|---|---|
| `open_equipment_card` | открыть карточку оборудования | `eq-n1a` |
| `view_signal` | посмотреть параметр | `PRA351` |
| `run_diagnostics` | запустить учебную диагностику | `eq-n1a` |
| `submit_decision` | зарегистрировать принятое решение | идентификатор объекта решения |
| `acknowledge_event` | подтвердить событие | идентификатор события |
| `submit_diagnosis` | отправить диагноз | `eq-n1a` |
| `start_pump` | запустить учебный насос | `eq-n1b` |
| `stop_pump` | остановить учебный насос | `eq-n1a` |

Открыть карточку Н-1А:

```json
{
  "actionType": "open_equipment_card",
  "targetId": "eq-n1a"
}
```

Посмотреть PRA 351:

```json
{
  "actionType": "view_signal",
  "targetId": "PRA351"
}
```

Допустимые основные сигналы сценария: `PRA351`, `FYQR117`, `LRCA605`.

Запустить диагностику Н-1А:

```json
{
  "actionType": "run_diagnostics",
  "targetId": "eq-n1a"
}
```

Отправить диагноз:

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

Допустимые `conclusion`: `fault_detected`, `no_fault`. Допустимые `reason`:
`bearing_wear`, `cavitation`, `electrical_overload`, `unknown`. Правильная пара
для текущего учебного сценария — `fault_detected` / `bearing_wear`.

Запустить резервный Н-1Б:

```json
{
  "actionType": "start_pump",
  "targetId": "eq-n1b"
}
```

Остановить неисправный Н-1А:

```json
{
  "actionType": "stop_pump",
  "targetId": "eq-n1a"
}
```

Допустимые насосы: `eq-n1`, `eq-n1a`, `eq-n1b`, `eq-n1v`. Диалог
подтверждения реализует frontend. При выборе «Отмена» сообщение не отправляется.

### Что backend возвращает в frontend

Сразу после подключения backend отправляет полный `telemetry.snapshot`.

После корректного действия сначала приходит подтверждение:

```json
{
  "type": "action.result",
  "status": "accepted",
  "actionId": "22222222-2222-2222-2222-222222222222",
  "stateVersion": 18
}
```

Затем всем подключённым клиентам сессии приходит новое `telemetry.update`.

Если действие невалидно или не может быть выполнено:

```json
{
  "type": "action.result",
  "status": "rejected",
  "error": {
    "code": "invalid_action",
    "message": "Action must contain a valid actionType, targetId and optional parameters"
  }
}
```

Коды ошибок действий:

- `invalid_message` — сообщение не является текстовым JSON;
- `invalid_action` — отсутствуют или невалидны поля действия;
- `session_not_found` — сессия недоступна;
- `session_not_running` — сессия не имеет статус `running`;
- `action_rejected` — неизвестная цель или действие отклонено моделью.

Ошибка действия не закрывает WebSocket.

### Телеметрия

Пример сокращённого сообщения:

```json
{
  "type": "telemetry.update",
  "sessionId": "11111111-1111-1111-1111-111111111111",
  "scenarioId": "MVP-SC-01",
  "scenarioVersion": "0.3.0",
  "modelId": "n1a-deterministic-training-model",
  "modelVersion": "0.3.0",
  "sequenceNo": 25,
  "stateVersion": 25,
  "timing": {
    "mode": "live",
    "elapsedMs": 55000,
    "totalMs": 120000,
    "remainingMs": 65000,
    "progressPercent": 45.8
  },
  "components": [
    {
      "componentId": "eq-n1a",
      "uiId": "pump-h1a",
      "tag": "Н-1А",
      "name": "Сырьевой насос Н-1А",
      "componentType": "pump",
      "status": "alert",
      "operatingState": "running",
      "parameters": [
        {
          "parameterId": "COMPAX.N1A.VELOCITY",
          "tag": "COMPAX.N1A.VELOCITY",
          "name": "Виброскорость Н-1А",
          "valuePercent": 375.0,
          "status": "alert"
        }
      ],
      "state": {
        "faultSeverityPercent": 68.3
      }
    }
  ],
  "journal": [
    {
      "entryId": "22222222-2222-2222-2222-222222222222",
      "time": "00:55",
      "description": "Запущен насос Н-1Б"
    }
  ]
}
```

`valuePercent` — нормализованное учебное значение. Физические единицы через
WebSocket не передаются. Допустимые статусы: `success`, `warning`, `alert`.

### Постоянный список компонентов

Список и порядок компонентов не меняются:

| `componentId` | `uiId` | Параметры |
|---|---|---|
| `eq-n1` | `pump-h1` | 5 параметров COMPACS |
| `eq-n1a` | `pump-h1a` | 5 параметров COMPACS |
| `eq-n1b` | `pump-h1b` | 5 параметров COMPACS |
| `eq-n1v` | `pump-h1v` | 5 параметров COMPACS |
| `eq-n1-discharge` | `line-n1-elou` | PRA 351, FYQR 117 |
| `eq-t1-t11` | `heat-exchanger-t1-t11` | расход, температура |
| `eq-elou` | `elou-block` | уровни I и II ступени |
| `eq-e15` | `e15` | LRCA 605 |

Остановленный насос остаётся в массиве, получает `operatingState = stopped`,
а его `parameters = []`. После запуска параметры появляются снова. Для
изменения отображения насоса frontend использует `operatingState`, а не общий
`status`.

В `state` компонента `eq-n1-discharge` дополнительно передаются:

- `recoveryActive` — идёт восстановление;
- `stabilized` — целевые значения достигнуты;
- `safePumpConfiguration` — достигнута безопасная учебная конфигурация;
- `scenarioFailed` и `failureReason` — терминальный отказ и его причина.

### Обработка сообщений на frontend

```javascript
socket.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === "action.result") {
    handleActionResult(message);
    return;
  }

  if (
    message.type === "telemetry.snapshot" ||
    message.type === "telemetry.update"
  ) {
    applyTelemetry(message);
  }
};
```

Правила применения телеметрии:

1. Проверять `sequenceNo` только у телеметрии и игнорировать старые сообщения.
2. Полностью заменять `components`, `timing` и `journal`.
3. Искать визуальный объект по `uiId`.
4. Значение брать из `valuePercent`, цвет — из `status`.
5. Журнал показывать колонками `time` и `description`.
6. После переподключения принять новый полный `telemetry.snapshot`.

Коды закрытия WebSocket: `4403` — запрещён Origin, `4404` — сессия не найдена,
`4409` — сессия не запущена.

### Где контракт реализован в коде

| Часть контракта | Файл |
|---|---|
| список `actionType` | `app/domain/enums.py`, класс `ActionType` |
| минимальное входное сообщение | `app/domain/actions.py`, класс `ScenarioActionRequest` |
| ответы `action.result` | `app/domain/actions.py`, классы `ActionAcceptedMessage` и `ActionRejectedMessage` |
| приём и отправка WebSocket | `app/api/routes/websocket.py` |
| создание UUID, времени и внутреннего действия | `app/services/session_manager.py`, метод `apply_scenario_action` |
| проверка целей и изменение модели | `app/simulation/model.py` |
| форматы snapshot/update | `app/domain/telemetry.py` |

## Статусы и завершение сценария

Статусы сессии: `created`, `running`, `paused`, `ready_to_complete`,
`completed`, `failed`, `cancelled`.

После стабилизации backend устанавливает `ready_to_complete` и останавливает
live-таймер. Frontend вызывает:

```http
POST /api/v1/sessions/{sessionId}/complete
GET  /api/v1/sessions/{sessionId}/result
GET  /api/v1/sessions/{sessionId}/actions
```

`result` содержит `rubricVersion`, итог, балл, секции оценки, штрафы,
`errorCodes` и `criticalFailureReasons`. `actions` содержит полный аудит с
виртуальным временем, описанием и ошибками для отчёта и будущего AI-модуля.

## Состояние и хранение

Активный расчёт модели живёт в памяти одного процесса FastAPI, поэтому MVP
запускается с одним worker. Метаданные сессий, все принятые действия и результаты
сохраняются в БД и доступны для последующего AI-анализа. После перезапуска можно
читать архив и результат, но продолжить незавершённый live-расчёт нельзя.

Redis/Kafka не требуются для одного worker. Внешний брокер понадобится при
горизонтальном масштабировании и нескольких экземплярах backend.

## Тесты (необязательно)

Тесты не запускаются автоматически вместе с Uvicorn и не блокируют merge:
сейчас в репозитории не настроен обязательный CI-check. При необходимости их
можно запустить вручную:

```bash
cd backend
KTK_DATABASE_URL=sqlite+pysqlite:///:memory: pytest
```

Основные проверки:

| Требование | Тест |
|---|---|
| REST lifecycle и результат | `test_session_api.py` |
| минимальные действия через WebSocket | `test_websocket_api.py` |
| полный пользовательский путь Н-1А | `test_full_scenario_api.py` |
| динамика и восстановление модели | `test_full_scenario.py` |
| хранение сессий, действий и результатов | `test_persistence.py` |
| миграции Alembic | `test_migrations.py` |
