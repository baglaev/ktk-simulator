# Контракт интеграции frontend с backend v2

## Локальные адреса

- REST API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- WebSocket: `ws://127.0.0.1:8000/ws/v1/sessions/{sessionId}`

Разрешённые Origin по умолчанию: `http://localhost:5173` и
`http://127.0.0.1:5173`.

## Последовательность подключения

1. `GET /api/v1/scenarios/MVP-SC-01/model-definition` — статическая модель,
   источники и учебные допущения.
2. `POST /api/v1/sessions` — создать сессию и сохранить `sessionId`.
3. `POST /api/v1/sessions/{sessionId}/start` — запустить live-сценарий.
4. Подключиться к `WS /ws/v1/sessions/{sessionId}`.
5. Действия пользователя отправлять через REST
   `POST /api/v1/sessions/{sessionId}/actions`.

Тело создания сессии:

```json
{
  "scenarioId": "MVP-SC-01",
  "traineeId": "trainee-001",
  "instructorId": "instructor-001",
  "mode": "training"
}
```

Сессия работает в live-режиме: одна секунда сценария соответствует одной
реальной секунде. Общая длительность текущего учебного профиля — 120 000 мс
(02:00). Это **учебное допущение**, а не производственный норматив.

## WebSocket-сообщения

Первое сообщение — `telemetry.snapshot`, следующие — `telemetry.update`.
Оба типа содержат полный массив `components` в одном и том же порядке.
Frontend может целиком заменять `timing`, `components` и `journal`.

Сокращённый пример:

```json
{
  "type": "telemetry.update",
  "sessionId": "11111111-1111-1111-1111-111111111111",
  "scenarioId": "MVP-SC-01",
  "scenarioVersion": "0.2.0",
  "modelId": "n1a-deterministic-training-model",
  "modelVersion": "0.2.0",
  "sequenceNo": 25,
  "stateVersion": 25,
  "timing": {
    "mode": "live",
    "elapsedMs": 25000,
    "totalMs": 120000,
    "remainingMs": 95000,
    "progressPercent": 20.8
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
          "valuePercent": 300.0,
          "status": "alert"
        }
      ],
      "state": {"faultSeverityPercent": 35.0}
    }
  ],
  "journal": [
    {
      "entryId": "22222222-2222-2222-2222-222222222222",
      "time": "00:25",
      "description": "Параметры диагностики Н-1А перешли в состояние alert"
    }
  ]
}
```

Числа траекторий модели — **учебные допущения**. WebSocket не передаёт
физические единицы: каждый динамический показатель называется
`valuePercent`. Паспортные значения и их исходные единицы остаются только в
статическом `model-definition` для прослеживаемости.

## Постоянный список компонентов

В каждом snapshot/update всегда присутствуют восемь экранных компонентов:

| `componentId` | `uiId` | Параметры |
|---|---|---|
| `eq-n1` | `pump-h1` | 5 параметров диагностики |
| `eq-n1a` | `pump-h1a` | 5 параметров диагностики |
| `eq-n1b` | `pump-h1b` | 5 параметров диагностики |
| `eq-n1v` | `pump-h1v` | 5 параметров диагностики |
| `eq-n1-discharge` | `line-n1-elou` | PRA 351, FYQR 117 |
| `eq-t1-t11` | `heat-exchanger-t1-t11` | расход, температура |
| `eq-elou` | `elou-block` | уровни I и II ступени |
| `eq-e15` | `e15` | LRCA 605 |

Допустимый UI-статус компонента и каждого параметра: `success`, `warning` или
`alert`. Поле `operatingState` отдельно сообщает режим оборудования
(`running`, `stopped` и т. п.); оно не используется как цвет Badge.

## Обработка на frontend

1. Применять сообщение, только если `sequenceNo` больше уже обработанного.
2. Для `telemetry.snapshot` и `telemetry.update` полностью заменять
   `components`, `timing` и `journal`.
3. На мнемосхеме искать компонент по `uiId`.
4. Badge брать из `status`, число — из `valuePercent` и добавлять `%` в UI.
5. Таймер строить из `timing.elapsedMs` или `timing.remainingMs`.
6. Журнал выводить колонками `time` и `description`; ключ строки — `entryId`.
7. После переподключения принять новый полный `telemetry.snapshot`.

`stateVersion` из последнего сообщения необходимо передавать как
`expectedStateVersion` при действии пользователя.

## Действия пользователя

```http
POST /api/v1/sessions/{sessionId}/actions
Content-Type: application/json

{
  "actionId": "22222222-2222-2222-2222-222222222222",
  "sessionId": "{sessionId}",
  "actionType": "run_diagnostics",
  "targetId": "eq-n1a",
  "expectedStateVersion": 25,
  "idempotencyKey": "diagnostics-n1a-1",
  "submittedAt": "2026-08-08T09:00:00+03:00"
}
```

Допустимые `actionType`: `open_equipment_card`, `view_signal`,
`run_diagnostics`, `submit_decision`, `acknowledge_event`. Успешное действие
появляется в `journal` следующего WebSocket-сообщения.

## Управление и ошибки

- `POST /api/v1/sessions/{sessionId}/pause`
- `POST /api/v1/sessions/{sessionId}/resume`
- `POST /api/v1/sessions/{sessionId}/complete`
- `GET /api/v1/sessions/{sessionId}`
- `GET /api/v1/sessions/{sessionId}/snapshot`

REST: `404` — объект не найден, `409` — конфликт состояния, `422` — неверное
тело. WebSocket: `4403` — Origin запрещён, `4404` — сессия не найдена,
`4409` — сессия ещё не запущена.

`POST /advance` является только служебным методом тестирования. Frontend его
не вызывает: live-таймер и расчёт выполняет backend автоматически.

Активные сессии MVP хранятся в памяти, поэтому backend запускается с одним
worker. Redis и Kafka для этого однопроцессного этапа не требуются.
