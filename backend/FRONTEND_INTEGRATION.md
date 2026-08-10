# Контракт frontend ↔ backend v4

## Адреса

- REST: `http://127.0.0.1:8000`
- Swagger REST: `http://127.0.0.1:8000/docs`
- WebSocket: `ws://127.0.0.1:8000/ws/v1/sessions/{sessionId}`

REST используется для жизненного цикла сессии и получения результата.
Действия пользователя внутри запущенного сценария и вся актуальная телеметрия
передаются через один двунаправленный WebSocket.

WebSocket не входит в OpenAPI и поэтому не показывается в Swagger. Его контракт
зафиксирован в этом документе и Pydantic-моделях `app/domain/actions.py` и
`app/domain/telemetry.py`.

## Последовательность работы frontend

1. `GET /api/v1/scenarios/MVP-SC-01/model-definition`.
2. `POST /api/v1/sessions` и сохранить `sessionId`.
3. `POST /api/v1/sessions/{sessionId}/start`.
4. Подключить WebSocket с полученным `sessionId`.
5. Применить первый `telemetry.snapshot`.
6. Кнопки отправляют минимальные JSON-действия в открытый WebSocket.
7. На `action.result` показать результат выполнения действия.
8. Состояние экрана обновлять из следующих `telemetry.update`.
9. Когда статус сессии `ready_to_complete`, разрешить «Завершить».
10. Вызвать REST `/complete`, затем получить REST `/result`.

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

Frontend отправляет действие текстовым JSON-сообщением в уже открытый
WebSocket:

```text
ws://127.0.0.1:8000/ws/v1/sessions/{sessionId}
```

Минимальное сообщение содержит только действие и его цель:

```json
{
  "actionType": "view_signal",
  "targetId": "PRA351"
}
```

Поля входного сообщения:

| Поле | Обязательность | Назначение |
|---|---|---|
| `actionType` | всегда | тип действия из списка ниже |
| `targetId` | для действий над объектом | идентификатор прибора или компонента |
| `parameters` | только когда нужны данные | дополнительные значения, например диагноз |

Frontend не передаёт `actionId`, `sessionId`, время, `stateVersion` и
`idempotencyKey`. Backend получает `sessionId` из WebSocket URL, берёт текущее
состояние модели, самостоятельно создаёт UUID и серверное время, а затем
сохраняет полную запись действия в БД.

Пример отправки из JavaScript:

```javascript
function sendScenarioAction(actionType, targetId, parameters) {
  const message = { actionType };

  if (targetId !== undefined) message.targetId = targetId;
  if (parameters !== undefined) message.parameters = parameters;

  socket.send(JSON.stringify(message));
}

sendScenarioAction("view_signal", "PRA351");
sendScenarioAction("start_pump", "eq-n1b");
```

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
  "targetId": "eq-n1b"
}
```

Останов неисправного Н-1А:

```json
{
  "actionType": "stop_pump",
  "targetId": "eq-n1a"
}
```

Допустимые идентификаторы учебных насосов: `eq-n1`, `eq-n1a`, `eq-n1b`,
`eq-n1v`. Диалог подтверждения реализует frontend. Если пользователь нажал
«Отмена», запрос не отправляется — ошибки и штрафа нет.

### Все допустимые `actionType`

| `actionType` | Ожидаемый `targetId` |
|---|---|
| `open_equipment_card` | компонент, например `eq-n1a` |
| `view_signal` | параметр: `PRA351`, `FYQR117` или `LRCA605` |
| `run_diagnostics` | диагностируемый компонент |
| `submit_decision` | объект принятого решения |
| `acknowledge_event` | подтверждаемое событие |
| `submit_diagnosis` | компонент; диагноз передаётся в `parameters` |
| `start_pump` | один из учебных насосов |
| `stop_pump` | один из учебных насосов |

## Что backend возвращает по WebSocket

### Подтверждение действия

Сначала отправителю возвращается результат обработки:

```json
{
  "type": "action.result",
  "status": "accepted",
  "actionId": "22222222-2222-2222-2222-222222222222",
  "stateVersion": 18
}
```

`actionId` и `stateVersion` генерирует backend. После подтверждения backend
отправляет новое `telemetry.update` всем клиентам этой сессии.

Если сообщение невалидно или действие нельзя выполнить:

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

- `invalid_message` — пришло не текстовое JSON-сообщение;
- `invalid_action` — отсутствуют или невалидны поля действия;
- `session_not_found` — сессия больше недоступна;
- `session_not_running` — сессия не находится в статусе `running`;
- `action_rejected` — неизвестная цель или действие противоречит модели.

### Телеметрия

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

1. Сначала проверить `type`: отдельно обрабатывать `action.result`,
   `telemetry.snapshot` и `telemetry.update`.
2. Проверять `sequenceNo` только у телеметрии; старые обновления игнорировать.
3. Полностью заменять `components`, `timing` и `journal` из телеметрии.
4. Искать визуальный объект по `uiId`.
5. Число брать из `valuePercent`, цвет — из `status`.
6. Журнал показывать колонками `time` и `description`.
7. Не отправлять действия, если `socket.readyState !== WebSocket.OPEN`.
8. После reconnect принять новый полный `telemetry.snapshot`.

REST-ошибки lifecycle и отчёта: `404` — не найдено, `409` — недопустимый
переход состояния, `422` — невалидное тело. WebSocket закрывается с кодом
`4403`, если Origin запрещён, `4404`, если сессия не найдена, и `4409`, если
сессия не запущена. Ошибка отдельного действия не закрывает соединение, а
возвращается сообщением `action.result` со статусом `rejected`.
