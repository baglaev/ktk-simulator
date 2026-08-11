# КТК ЭЛОУ-АВТ

Компьютерный тренажёрный комплекс с учебной моделью сценария отказа сырьевого
насоса Н-1А, live-телеметрией через WebSocket и AI-модулем для итогового разбора
и послесессионного RAG.

Все численные траектории, пороги и временные окна сценария являются учебными
допущениями и не должны использоваться как производственные инструкции или
уставки оборудования.


**Важно! Схема симулятора установки на странице /simulator корректно отображается и работает при ширине экрана 1680 пикселей**

**Данные для авторизации пользователей**

Инструктор: 
логин: Petrov.PP
пароль: instructor

Обучаемый:
логин: Ivanov.II
пароль: user


## Состав проекта

- `frontend/` — пользовательский интерфейс тренажёра;
- `backend/` — FastAPI, модель сценария, WebSocket, REST API и база данных;
- `ai/` — детерминированный анализ, OpenRouter, резервный профиль VK Cloud и локальный RAG;
- `run_backend_ai.sh` — единый запуск backend и AI.



AI не является отдельным сервером. Он подключается к backend как Python-модуль
и вызывается при формировании итогового анализа или ответа RAG.

## Первичная установка backend

Обычно отдельная установка не нужна: `run_backend_ai.sh` сам создаёт
`backend/.venv`, если окружения ещё нет, и устанавливает зависимости backend и
AI из `backend/requirements.txt`.

Для ручной установки из корня репозитория:

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
AI_LLM_PROVIDER=openrouter
AI_LLM_BASE_URL=https://openrouter.ai/api/v1
AI_LLM_MODEL=google/gemma-4-26b-a4b-it:free
AI_LLM_FALLBACK_MODEL=openrouter/free
OPENROUTER_API_KEY=ваш-секретный-ключ
```

Файл `ai/.env` не добавляется в Git. Если основная модель недоступна, backend
один раз повторяет запрос через `openrouter/free`. Если не сработали обе модели,
система возвращает детерминированный анализ без LLM.

### Резервный профиль VK Cloud

Клиент также готов к локально развёрнутой модели в VK Cloud через
OpenAI-совместимый сервер vLLM. Сейчас этот профиль не активен. После запуска
модели на облачной ВМ переключение выполняется только настройками `ai/.env`:

```dotenv
AI_LLM_ENABLED=true
AI_LLM_PROVIDER=vk_cloud
AI_VK_CLOUD_BASE_URL=http://127.0.0.1:8001/v1
AI_VK_CLOUD_MODEL=ktk-qwen
AI_VK_CLOUD_API_KEY=секретный-ключ-vllm
```

`127.0.0.1` подходит, если backend и vLLM работают на одной ВМ. Для разных ВМ
нужно указать приватный IP модели и разрешить доступ только из внутренней сети.
Переключение явное: при `vk_cloud` система не отправляет резервный запрос в
OpenRouter. До перехода на локальную модель во внешний OpenRouter разрешено
передавать только учебные обезличенные данные — без персональных, секретных и
реальных производственных сведений.

## Запуск backend и AI

Из корня репозитория выполните:

```bash
./run_backend_ai.sh
```

Скрипт:

1. создаёт `backend/.venv`, если его ещё нет;
2. проверяет и устанавливает объявленные зависимости из
   `backend/requirements.txt`;
3. загружает `ai/.env`;
4. проверяет ключ и настройки модели;
5. выполняет `alembic upgrade head`;
6. запускает FastAPI вместе с подключённым AI-модулем.

Backend и AI используют одно Python-окружение. В частности, библиотека
`reportlab`, необходимая для PDF-отчёта, устанавливается автоматически.
Повторный запуск безопасен: `pip` не переустанавливает уже подходящие версии.

Чтение PDF-документов при построении RAG-индекса дополнительно требует системную
утилиту `pdftotext`. На macOS она устанавливается командой:

```bash
brew install poppler
```

Если зависимости уже установлены или запуск выполняется без доступа в интернет,
проверку можно пропустить:

```bash
KTK_INSTALL_DEPENDENCIES=false ./run_backend_ai.sh
```

После запуска доступны:

- backend: [http://127.0.0.1:8000](http://127.0.0.1:8000);
- проверка состояния: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health);
- Swagger REST API: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs);
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

Frontend доступен по адресам [http://localhost:5173/](http://localhost:5173/) [http://127.0.0.1:5173/](http://127.0.0.1:5173/).

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
