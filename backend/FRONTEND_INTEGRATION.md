# Контракт интеграции frontend с backend

## Адреса для локальной разработки

- REST API: `http://127.0.0.1:8000`
- OpenAPI: `http://127.0.0.1:8000/docs`
- WebSocket: `ws://127.0.0.1:8000/ws/v1/sessions/{sessionId}`
- Frontend Origin: `http://localhost:5173` или `http://127.0.0.1:5173`

Другие Origin необходимо добавить в `KTK_CORS_ALLOWED_ORIGINS`.

## Последовательность запуска

### 1. Получить определение модели

```http
GET /api/v1/scenarios/MVP-SC-01/model-definition
```

Ответ содержит статические описания оборудования, сигналов, единиц измерения,
связей, источников и учебных допущений. Его не нужно запрашивать на каждом
WebSocket-сообщении.

### 2. Создать сессию

```http
POST /api/v1/sessions
Content-Type: application/json

{
  "scenarioId": "MVP-SC-01",
  "traineeId": "trainee-001",
  "mode": "training"
}
```

Из ответа необходимо сохранить `sessionId`.

### 3. Запустить сессию

```http
POST /api/v1/sessions/{sessionId}/start
```

### 4. Подключить WebSocket

```text
ws://127.0.0.1:8000/ws/v1/sessions/{sessionId}
```

Первое сообщение всегда имеет тип `telemetry.snapshot` и содержит полное
состояние. Затем backend автоматически отправляет `telemetry.delta`.
Frontend не должен запускать таймер расчёта и регулярно вызывать `/advance`.

Сокращённый пример snapshot:

```json
{
  "type": "telemetry.snapshot",
  "sessionId": "11111111-1111-1111-1111-111111111111",
  "scenarioId": "MVP-SC-01",
  "scenarioVersion": "0.1.0",
  "modelId": "n1a-deterministic-training-model",
  "modelVersion": "0.1.0",
  "sequenceNo": 0,
  "stateVersion": 0,
  "virtualTimeMs": 0,
  "equipment": [
    {
      "equipmentId": "eq-n1a",
      "status": "running",
      "state": {"faultSeverity": 0.0, "diagnosticStatus": "normal"}
    }
  ],
  "signals": [
    {
      "signalId": "PRA351",
      "value": 100.0,
      "quality": "good",
      "virtualTimeMs": 0
    }
  ],
  "events": []
}
```

Delta имеет тот же envelope, но массивы содержат только изменившиеся элементы:

```json
{
  "type": "telemetry.delta",
  "sessionId": "11111111-1111-1111-1111-111111111111",
  "scenarioId": "MVP-SC-01",
  "scenarioVersion": "0.1.0",
  "modelId": "n1a-deterministic-training-model",
  "modelVersion": "0.1.0",
  "sequenceNo": 1,
  "stateVersion": 1,
  "virtualTimeMs": 1000,
  "equipment": [],
  "signals": [
    {
      "signalId": "COMPAX.N1A.TEMPERATURE",
      "value": 61.0,
      "quality": "good",
      "virtualTimeMs": 1000
    }
  ],
  "events": []
}
```

Числа в примерах — **учебное допущение** для демонстрации формата контракта.
Фактические значения необходимо брать только из полученного сообщения.

## Обработка телеметрии

Ключи коллекций:

- оборудование — `equipmentId`;
- сигналы — `signalId`;
- события — `eventId`.

Алгоритм frontend:

1. На `telemetry.snapshot` полностью заменить локальное состояние.
2. На `telemetry.delta` заменить только переданные элементы оборудования и
   сигналов по их идентификаторам.
3. Новые события добавить в журнал без дубликатов по `eventId`.
4. Сохранить последние `sequenceNo`, `stateVersion` и `virtualTimeMs`.
5. Применять сообщение только если его `sequenceNo` больше последнего
   применённого. Пропуск номеров допустим: backend может объединить несколько
   промежуточных состояний в одну актуальную delta для медленного клиента.
6. После разрыва соединения переподключить WebSocket: новым первым сообщением
   будет полный актуальный snapshot.

`virtualTimeMs` — время учебной модели. Оно не является серверным timestamp.
`stateVersion` необходимо передавать как `expectedStateVersion` в действии.

## Действия обучаемого

```http
POST /api/v1/sessions/{sessionId}/actions
Content-Type: application/json

{
  "actionId": "22222222-2222-2222-2222-222222222222",
  "sessionId": "{sessionId}",
  "actionType": "run_diagnostics",
  "targetId": "eq-n1a",
  "expectedStateVersion": 12,
  "idempotencyKey": "diagnostics-n1a-1",
  "submittedAt": "2026-08-08T09:00:00+03:00"
}
```

`actionId` должен быть UUID, `idempotencyKey` — уникальным для логического
действия. При `409 Conflict` из-за устаревшей версии следует получить актуальное
состояние и попросить пользователя повторить действие, если оно всё ещё нужно.

Допустимые `actionType`: `open_equipment_card`, `view_signal`,
`run_diagnostics`, `submit_decision`, `acknowledge_event`.

## Управление сессией

```text
POST /api/v1/sessions/{sessionId}/pause
POST /api/v1/sessions/{sessionId}/resume
POST /api/v1/sessions/{sessionId}/complete
GET  /api/v1/sessions/{sessionId}
GET  /api/v1/sessions/{sessionId}/snapshot
```

`pause` прекращает продвижение виртуального времени, `resume` продолжает его.
Сессия автоматически получает статус `completed` при достижении границы
учебного сценария.

## Ошибки

- REST `404` — сценарий или сессия не найдены.
- REST `409` — недопустимый lifecycle-переход или конфликт версии состояния.
- REST `422` — тело запроса не соответствует контракту.
- WebSocket `4403` — Browser Origin не разрешён.
- WebSocket `4404` — сессия не найдена.
- WebSocket `4409` — сессия ещё не запущена.

## Ограничения текущего MVP

- Активные сессии хранятся в памяти и теряются при перезапуске backend.
- Backend необходимо запускать с одним worker.
- Коэффициент виртуального времени и траектории модели являются учебными
  допущениями, описанными в версии сценария.
- Redis и Kafka не требуются для однопроцессного MVP.
