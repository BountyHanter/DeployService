# DeployService

Сервис принимает GitHub webhook `push`, проверяет подпись `sha256`, и запускает `deploy.sh` внутри каталога проекта. Опционально отправляет уведомления в Telegram. Логи пишет в читаемом и JSON формате (см. `fast_api_logger/Readme.md`).

## Как работает

1. GitHub присылает webhook `push`.
2. Сервис проверяет подпись `X-Hub-Signature-256` по `WEBHOOK_SECRET`.
3. Если это `push` в `main`, запускается `deploy.sh` в каталоге проекта.
4. Результат запуска фиксируется в логах и (опционально) в Telegram.

## Требования

- Python 3.10+
- Зависимости из `requirements.txt`
- Для venv в Ubuntu/Debian: `sudo apt install python3.10-venv`
- Для pip в Ubuntu/Debian: `sudo apt install python3-pip`

Примечание: на момент написания документации venv и pip ставятся этими командами. Если версия Python в системе другая — проверь актуальные команды для своей версии.

Локальная установка:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Переменные окружения

Скопируй и заполни `.env` на основе `.env.example`:

```env
WEBHOOK_SECRET=
PROJECTS_ROOT=/var/www

TG_BOT_TOKEN=
TG_CHAT_ID=

LOG_LEVEL=INFO
LOG_NAME=deploy-service
```

Описание:

- `WEBHOOK_SECRET` — секрет для подписи GitHub webhook. (Можно сгенерировать: `openssl rand -hex 32`)
- `PROJECTS_ROOT` — путь, где лежат проекты для деплоя. Дефолт `/var/www`.
- `TG_BOT_TOKEN`, `TG_CHAT_ID` — опционально, для Telegram уведомлений.
- `LOG_LEVEL`, `LOG_NAME` — параметры логгера.

## Запуск

Локально:

```bash
uvicorn main:app --host 0.0.0.0 --port 9999
```

## Проверка работы сервиса

```bash
curl http://localhost:9999/health
```

## Быстрое развёртывание (systemd)

1. Создай `.env` из `.env.example` и заполни.
2. Запусти:

```bash
sudo ./deploy_native.sh
```

Скрипт:

- создаёт `.venv`,
- устанавливает зависимости из `requirements.txt`,
- создаёт systemd-сервис `deploy-webhook.service` (если нет),
- запускает сервис,
- ждёт 10 секунд и сам проверяет `/health` (5 попыток).

Опциональные переменные для `deploy_native.sh`:

- `PROJECT_DIR` (по умолчанию `/var/www/DeployWebhook`)
- `SERVICE_NAME` (по умолчанию `deploy-webhook`)
- `PORT` (по умолчанию `9999`)
- `HEALTH_URL` (по умолчанию `http://127.0.0.1:9999/health`)
- `ATTEMPTS` (по умолчанию `5`)
- `WAIT_STARTUP` (по умолчанию `10`)
- `PULL_REMOTE` (по умолчанию `origin`)
- `PULL_BRANCH` (по умолчанию `main`)
- `SERVICE_USER`, `SERVICE_GROUP` (по умолчанию текущий пользователь)

## Настройка GitHub Webhook

В GitHub для нужного репозитория:

1. Открой `Settings` → `Webhooks` → `Add webhook`.
2. Заполни:

- `Payload URL`: `https://<your-domain>/deploy` (можно без домена и SSL но это не безопасно для крупных проектов)
- `Content type`: `application/json`
- `Secret`: значение из `WEBHOOK_SECRET`
- `SSL verification`: включено (рекомендуется)
- `Which events would you like to trigger this webhook?`: `Just the push event`

3. Нажми `Add webhook`.

### Важно

- Деплой запускается **только** для `push` в ветку `main`.
- Если `deploy.sh` не найден — вернётся 404 и будет отправлено уведомление в Telegram (если настроен).
- Сервис умеет **автоматически запускать деплой проектов** по webhook от GitHub, но **сам себя обновлять не может**. Поэтому обновление/установка самого сервиса делается вручную через `deploy_native.sh`.

## Требования к проекту для деплоя

В каждом проекте должен быть `deploy.sh`:

```
/var/www/<repo_name>/deploy.sh
```

Сервис запускает его через `subprocess.Popen(...)` с `cwd` на корень проекта.

## Логи

Логи пишутся в `logs/`:

- `logs/app.log` — читаемый формат
- `logs/app.json.log` — JSON формат

Подробности см. в `fast_api_logger/Readme.md`.
