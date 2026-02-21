#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/var/www/DeployService}"
SERVICE_NAME="${SERVICE_NAME:-deploy-webhook}"
PORT="${PORT:-9999}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:${PORT}/health}"
ATTEMPTS="${ATTEMPTS:-5}"
WAIT_STARTUP="${WAIT_STARTUP:-10}"
PULL_REMOTE="${PULL_REMOTE:-origin}"
PULL_BRANCH="${PULL_BRANCH:-main}"
SERVICE_USER="${SERVICE_USER:-${SUDO_USER:-$USER}}"
SERVICE_GROUP="${SERVICE_GROUP:-$SERVICE_USER}"

if [ "$EUID" -ne 0 ]; then
  echo "Запусти скрипт через sudo: sudo ./deploy_native.sh" >&2
  exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  echo "Пользователь '$SERVICE_USER' не найден. Укажи SERVICE_USER через переменную окружения." >&2
  exit 1
fi

if [ ! -d "$PROJECT_DIR" ]; then
  echo "Директория проекта не найдена: $PROJECT_DIR" >&2
  exit 1
fi

run_as_user() {
  local cmd="$1"
  su -s /bin/bash -c "$cmd" "$SERVICE_USER"
}

cd "$PROJECT_DIR"

echo "Получаем изменения из репозитория..."
run_as_user "git pull '$PULL_REMOTE' '$PULL_BRANCH'"

if [ ! -f "$PROJECT_DIR/.env" ]; then
  echo "Файл .env отсутствует в $PROJECT_DIR" >&2
  echo "Создай его из .env.example перед запуском деплоя." >&2
  exit 1
fi

if [ ! -x "$PROJECT_DIR/.venv/bin/python" ]; then
  echo "Создаём виртуальное окружение..."
  run_as_user "python -m venv '$PROJECT_DIR/.venv'"
fi

echo "Устанавливаем зависимости..."
run_as_user "'$PROJECT_DIR/.venv/bin/pip' install --upgrade pip"
run_as_user "'$PROJECT_DIR/.venv/bin/pip' install -r '$PROJECT_DIR/requirements.txt'"

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [ ! -f "$SERVICE_FILE" ]; then
  echo "Создаём systemd-сервис..."

  cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Deploy Webhook Service
After=network.target

[Service]
Type=simple
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
Environment=PORT=${PORT}
Environment=PYTHONUNBUFFERED=1
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
ExecStart=${PROJECT_DIR}/.venv/bin/uvicorn main:app --host 0.0.0.0 --port \${PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

  systemctl daemon-reload
  systemctl enable --now "${SERVICE_NAME}.service"
else
  echo "Перезапускаем systemd-сервис..."
  systemctl restart "${SERVICE_NAME}.service"
fi

echo "Ожидаем запуск приложения..."
sleep "$WAIT_STARTUP"

SUCCESS=false

for i in $(seq 1 "$ATTEMPTS"); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || true)

  if [ "$STATUS" = "200" ]; then
    SUCCESS=true
    break
  fi

  echo "Попытка проверки health ($i) не удалась..."
  sleep 2
done

if [ "$SUCCESS" = true ]; then
  echo "Деплой успешно завершён"
else
  echo "Деплой завершился с ошибкой: health endpoint не вернул 200"
  exit 1
fi