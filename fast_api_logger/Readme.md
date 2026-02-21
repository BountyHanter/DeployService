# Fast Api Logger — пользовательская документация
Последнее изменение 02.02.2026

## Что это

**Fast Api Logger** — универсальный логгер для Python / FastAPI проектов, который:

* можно **скопировать и использовать без правок кода**,
* настраивается **только через env**,
* пишет:

  * читаемые логи (для человека),
  * JSON-логи (для машин / сервисов),
* безопасен для **async / streaming / SSE**,
* поддерживает **контекст логирования** (request_id и любые кастомные поля).

---

## Быстрый старт

### Подключение

```python
from fast_api_logger import log

log.info("Service started")
```

Ничего больше делать не нужно.

---

## Уровни логов

Используются стандартные методы:

* `log.debug(...)`
* `log.info(...)`
* `log.warning(...)`
* `log.error(...)` — ошибка **без traceback**
* `log.exception(...)` — ошибка **с traceback** (использовать внутри `except`)

Пример:

```python
try:
    1 / 0
except Exception:
    log.exception("Unhandled error")
```

---

## Контекст логирования (contextvars)

### Зачем нужен контекст

Контекст нужен, чтобы **не передавать одни и те же поля через `extra` в каждом логе**.

Типичный пример — `request_id`.

Без контекста:

```python
log.info("Request received", extra={"request_id": rid})
log.info("User created", extra={"request_id": rid})
```

С контекстом:

```python
set_context(request_id=rid)

log.info("Request received")
log.info("User created")
```

`request_id` автоматически попадёт во все логи.

---

## Работа с контекстом

### Основные функции

```python
from fast_api_logger.context import (
  set_context,
  remove_context,
  clear_context,
  get_context,
)
```

### `set_context(**kwargs)`

Добавляет или обновляет поля контекста.

```python
set_context(
    request_id="req_123",
    service="gpt-backend",
    env="prod"
)
```

### `remove_context(*keys)`

Удаляет ключи из контекста.

```python
remove_context("user_id", "chat_id")
```

### `clear_context()`

Полностью очищает контекст (рекомендуется в конце запроса).

---

## Специализированные хелперы (расширяемые)

В `context.py` есть раздел **CUSTOM HELPERS**.

Пример готового хелпера:

```python
set_request_id("req_123")
```

Ты можешь **свободно добавлять свои**:

```python
def set_user_id(user_id: int | None) -> None:
    if user_id is None:
        remove_context("user_id")
    else:
        set_context(user_id=user_id)
```

### Рекомендации по контексту

✅ Класть в контекст:

* `request_id`
* `trace_id`
* `service`
* `env`
* `session_id`

❌ Не класть:

* объекты (`Request`, `Run`, `Thread`)
* большие структуры
* часто меняющиеся данные

---

## `extra` vs контекст — что когда использовать

### Контекст

Используй для **глобальных идентификаторов запроса**:

* request_id
* service
* env

### `extra`

Используй для **локальных данных события**:

```python
log.info("User created", extra={"user_id": 42})
```

❗ `extra` **имеет приоритет** над контекстом.

---

## Stream-safe логирование

### Проблема

При использовании `StreamingResponse` / SSE **любой вывод в stdout** может:

* сломать поток,
* привести к «тихому обрыву»,
* вызвать ошибки у клиента.

---

### Решение

Fast Api Logger разделяет:

* **политику** (через env),
* **текущее состояние выполнения** (через код).

---

### Переменная окружения `STREAM_SAFE`

```env
STREAM_SAFE=true
```

Означает:

> «В этом проекте stdout нельзя использовать во время стрима».

Если `STREAM_SAFE=false`, логгер **никогда не подавляет stdout**, даже во время стрима.

---

### `set_streaming(True | False)`

Функции из `context.py`:

```python
from fast_api_logger.context import set_streaming
```

Используются, чтобы **сообщить логгеру**, что:

* `True` — код сейчас выполняется внутри стрима,
* `False` — стрим закончился.

---

### Как использовать в стриминге (обязательно)

```python
async def event_generator():
    set_streaming(True)
    try:
        log.info("Stream started")
        ...
        yield ...
    finally:
        set_streaming(False)
        log.info("Stream finished")
```

---

### Почему нужны И `STREAM_SAFE`, И `set_streaming`

* `STREAM_SAFE` — **глобальная политика проекта** (через env)
* `set_streaming` — **факт текущего исполнения** (через код)

Логгер подавляет stdout **только если оба условия true**.

Это позволяет:

* управлять поведением **без изменения кода**,
* использовать логгер в проектах **без стриминга**,
* быстро отключить stream-safe для дебага.

---

## Переменные окружения (ENV)

### Основные

```env
LOG_LEVEL=INFO
LOG_NAME=app
```

---

### Консоль

```env
LOG_CONSOLE=true
LOG_CONSOLE_FORMAT=text   # text | json
```

---

### Файлы логов

```env
LOG_FILE_TEXT=true
LOG_FILE_TEXT_PATH=logs/app.log

LOG_FILE_JSON=true
LOG_FILE_JSON_PATH=logs/app.json.log
```

---

### Ротация логов

```env
LOG_ROTATION_WHEN=midnight   # midnight | H | D | M
LOG_ROTATION_INTERVAL=1
LOG_ROTATION_BACKUP=7
LOG_ROTATION_UTC=false
```

---

### Поведение

```env
LOG_SANITIZE_EXTRA=true
STREAM_SAFE=true
```

---

## Рекомендуемый шаблон для FastAPI middleware

```python
@app.middleware("http")
async def context_middleware(request: Request, call_next):
    try:
        set_context(
            request_id=request.headers.get("X-Request-ID"),
            service="gpt-backend",
            env="prod",
        )
        response = await call_next(request)
        return response
    finally:
        clear_context()
```

---

## Логи uvicorn (FastAPI / Uvicorn)

Fast Api Logger **не настраивает логи uvicorn автоматически**.

Это сделано осознанно, чтобы:

* логгер оставался универсальным (подходит не только для FastAPI),
* не вмешиваться в конфигурацию веб-сервера без явного указания,
* избежать конфликтов с существующими настройками uvicorn / gunicorn.

### Когда это нужно

Рекомендуется настраивать отдельные логи uvicorn, если ты хочешь:

* разделить **логи приложения** и **логи сервера**,
* сохранять читаемые traceback’и ошибок uvicorn,
* не смешивать HTTP/access логи с бизнес-логикой приложения.

---

### Как подключить логи uvicorn

Создай (или используй) модуль интеграции, например:

```
fast_api_logger/uvicorn.py
```

Инициализируй его **один раз при старте приложения**, например в `main.py`:

```python
from fast_api_logger.uvicorn import configure_uvicorn_logging

configure_uvicorn_logging(
    error_log_path="logs/uvicorn_error.log",
    access_log_path="logs/uvicorn_access.log",
)
```

После этого:

* ошибки uvicorn (`uvicorn.error`) будут писаться в `uvicorn_error.log`,
* HTTP/access-логи (`uvicorn.access`) — в `uvicorn_access.log`,
* логи приложения (`log.info(...)`) остаются в `app.log` / `app.json.log`.

---

### Важно

* Fast Api Logger **не требует** настройки uvicorn-логов — это опционально.
* Если разделение логов не нужно, этот шаг можно пропустить.
* Настройка uvicorn-логов **не влияет** на `STREAM_SAFE` и контекст логирования.

---

## Краткий итог

* Контекст — для глобальных идентификаторов запроса
* `extra` — для локальных данных события
* `STREAM_SAFE` — политика проекта
* `set_streaming` — состояние исполнения
* Логгер не гадает, не магичит, не ломает стримы
