# Backend MVP — проверка пользовательского пути

Численные правила ниже являются учебными допущениями `A-17`/`A-18` из
`GET /api/v1/scenarios/MVP-SC-01/model-definition`.

| Требование | Реализация | Проверка |
|---|---|---|
| Live-таймер | `services/simulation_runtime.py` | `test_runtime_integration.py` |
| Warning Н-1А на 10 с | профиль + `simulation/model.py` | `test_n1a_process_model.py` |
| Просмотр PRA 351/FYQR 117 | `view_signal` | `test_full_scenario.py` |
| Диагноз и причина | `submit_diagnosis` | `test_full_scenario_api.py` |
| Запуск Н-1Б, останов Н-1А | `start_pump`, `stop_pump` | `test_full_scenario.py` |
| Скрытие параметров остановленного насоса | `components[].parameters = []` | `test_full_scenario.py` |
| Безопасная конфигурация | `has_safe_configuration()` | `test_full_scenario.py` |
| Линейное восстановление 30 с | `simulation/model.py` | `test_full_scenario.py` |
| LRCA 605 = 20% → failed | lifecycle менеджера | `test_full_scenario.py` |
| Ошибочная диагностика не меняет физику | модель действий | `test_full_scenario.py` |
| Оценка 0–100 и штрафы | `evaluation/deterministic.py` | `test_full_scenario.py` |
| Журнал действий и ошибок | `RecordedAction` | `test_full_scenario_api.py` |
| Сессии/действия/результаты в БД | SQLAlchemy + Alembic | `test_persistence.py` |
| REST-контракт | FastAPI/Pydantic | `test_full_scenario_api.py` |
| WebSocket-контракт | snapshot/update | `test_websocket_api.py` |

Текущая граница MVP: активное состояние численной модели остаётся в памяти
одного worker. После рестарта архив сессии, действия и результат доступны из
БД, но незавершённый live-расчёт не возобновляется.
