# Контракт frontend ↔ backend v3

## Адреса

- REST: `http://127.0.0.1:8000`
- Swagger REST: `http://127.0.0.1:8000/docs`
- WebSocket: `ws://127.0.0.1:8000/ws/v1/sessions/{sessionId}`

WebSocket не входит в OpenAPI и поэтому не показывается в Swagger. Его формат
зафиксирован в этом документе и Pydantic-моделях `app/domain/telemetry.py`.

## Последовательность работы frontend

1. `GET /api/v1/scenarios/MVP-SC-01/model-definition`.
2. `POST /api/v1/sessions` и сохранить `sessionId`.
3. `POST /api/v1/sessions/{sessionId}/start`.
4. Подключить WebSocket с полученным `sessionId`.
5. Применить первый `telemetry.snapshot`.
6. Кнопки отправляют REST-действия в `/actions`.
7. Состояние экрана обновлять из следующих `telemetry.update`.
8. Когда статус сессии `ready_to_complete`, разрешить «Завершить».
9. Вызвать `/complete`, затем получить `/result`.

Создание сессии:

```json
{
  "scenarioId": "MVP-SC-01",
  "traineeId": "trainee-001",
  "instructorId": "instructor-001",
  "mode": "training"
}
```

## Действия пользователя

Все действия отправляются в:

```http
POST /api/v1/sessions/{sessionId}/actions
Content-Type: application/json
```

Общие поля:

```json
{
  "actionId": "новый UUID",
  "sessionId": "UUID из POST /sessions",
  "actionType": "view_signal",
  "targetId": "PRA351",
  "parameters": {},
  "expectedStateVersion": 17,
  "idempotencyKey": "уникальная строка для одного клика",
  "submittedAt": "2026-08-10T12:00:00+03:00"
}
```

`expectedStateVersion` брать из последнего WebSocket-сообщения или REST-ответа.
Успешный `/actions` возвращает новый полный snapshot и одновременно публикует
его в WebSocket. При устаревшей версии backend возвращает `409`.

### Просмотр

- открыть карточку: `actionType = open_equipment_card`, `targetId = eq-n1a`;
- посмотреть параметр: `actionType = view_signal`, например `PRA351`,
  `FYQR117`, `LRCA605`.

### Диагностика

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

Допустимые `conclusion`: `fault_detected`, `no_fault`.

Допустимые `reason`: `bearing_wear`, `cavitation`, `electrical_overload`,
`unknown`. Для текущего учебного сценария правильная пара —
`fault_detected` / `bearing_wear`.

### Управление насосами

Запуск резервного Н-1Б:

```json
{
  "actionType": "start_pump",
  "targetId": "eq-n1b",
  "parameters": {}
}
```

Останов неисправного Н-1А:

```json
{
  "actionType": "stop_pump",
  "targetId": "eq-n1a",
  "parameters": {}
}
```

Допустимые идентификаторы учебных насосов: `eq-n1`, `eq-n1a`, `eq-n1b`,
`eq-n1v`. Диалог подтверждения реализует frontend. Если пользователь нажал
«Отмена», запрос не отправляется — ошибки и штрафа нет.

## WebSocket-сообщение

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
      "state": {"faultSeverityPercent": 68.3}
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

## Постоянный список компонентов

Порядок и состав всегда одинаковы:

| `componentId` | `uiId` | Параметры |
|---|---|---|
| `eq-n1` | `pump-h1` | 5 COMPACS |
| `eq-n1a` | `pump-h1a` | 5 COMPACS |
| `eq-n1b` | `pump-h1b` | 5 COMPACS |
| `eq-n1v` | `pump-h1v` | 5 COMPACS |
| `eq-n1-discharge` | `line-n1-elou` | PRA 351, FYQR 117 |
| `eq-t1-t11` | `heat-exchanger-t1-t11` | расход, температура |
| `eq-elou` | `elou-block` | уровни I и II ступени |
| `eq-e15` | `e15` | LRCA 605 |

Остановленный насос остаётся в массиве, получает `operatingState = stopped`,
а его `parameters = []`. После запуска параметры снова появляются. Именно
`operatingState`, а не `status`, должен делать насос серым и менять кнопку
«Запустить» / «Остановить».

Для `eq-n1-discharge` в `state` дополнительно приходят:

- `recoveryActive` — идёт 30-секундное восстановление;
- `stabilized` — целевые значения достигнуты;
- `safePumpConfiguration` — выполнена безопасная конфигурация.
- `scenarioFailed` и `failureReason` — терминальный отказ и его причина.

## Правила live-модели

На 10-й секунде Н-1А становится `warning`. Восстановление запускается только
если Н-1Б работает, Н-1А остановлен, Н-1 и Н-1В работают. Оно линейно длится
30 секунд. PRA 351, FYQR 117 и уровни ЭЛОУ идут к 100%, LRCA 605 — к 65%.

Если LRCA 605 достиг 20% до запуска восстановления, сессия становится
`failed`. Если восстановление начато раньше при значении строго выше 20%, ему
разрешается закончиться после отметки 120 секунд. Это **учебное допущение**.
В `model-definition` правило имеет идентификатор `A-17`; методика статусов и
оценки — `A-18`.

## Статусы и завершение

Статусы сессии: `created`, `running`, `paused`, `ready_to_complete`,
`completed`, `failed`, `cancelled`.

После стабилизации backend ставит `ready_to_complete` и останавливает live-таймер.
Frontend вызывает:

```http
POST /api/v1/sessions/{sessionId}/complete
GET  /api/v1/sessions/{sessionId}/result
GET  /api/v1/sessions/{sessionId}/actions
```

`result` содержит `rubricVersion`, `outcome`, `totalScore`, четыре секции баллов, `penalties`,
`errorCodes` и `criticalFailureReasons`. `/actions` содержит весь аудит с
`virtualTimeMs`, описанием и ошибками — это вход для будущего AI-модуля.

## Правила применения сообщений

1. Игнорировать сообщение, если `sequenceNo` не больше уже применённого.
2. Полностью заменять `components`, `timing` и `journal`.
3. Искать визуальный объект по `uiId`.
4. Число брать из `valuePercent`, цвет — из `status`.
5. Журнал показывать колонками `time` и `description`.
6. После reconnect принять новый полный `telemetry.snapshot`.

REST-ошибки: `404` — не найдено, `409` — конфликт lifecycle/stateVersion,
`422` — невалидное тело. WebSocket: `4403` — Origin запрещён, `4404` — сессия
не найдена, `4409` — сессия не запущена.
