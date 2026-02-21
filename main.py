import os
import hmac
import hashlib
import subprocess
import threading
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

from fast_api_logger import log
from fast_api_logger.context import set_context, clear_context

load_dotenv()

app = FastAPI()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
PROJECTS_ROOT = os.getenv("PROJECTS_ROOT", "/var/www")

TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")


# =====================================================
# TELEGRAM
# =====================================================
async def send_tg(message: str):
    if not TG_TOKEN or not TG_CHAT_ID:
        log.warning("Telegram отключён (нет токена)")
        return

    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"

    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(
            url,
            data={
                "chat_id": TG_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
            },
        )


# =====================================================
# VERIFY SIGNATURE
# =====================================================
def verify_signature(body: bytes, signature: str | None) -> bool:
    if not signature:
        return False

    try:
        sha_name, received = signature.split("=")
    except ValueError:
        return False

    if sha_name != "sha256":
        return False

    mac = hmac.new(
        WEBHOOK_SECRET.encode(),
        msg=body,
        digestmod=hashlib.sha256,
    )

    return hmac.compare_digest(mac.hexdigest(), received)


# =====================================================
# WEBHOOK
# =====================================================
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/deploy")
async def deploy(request: Request):

    body = await request.body()

    # --- базовый контекст запроса ---
    set_context(
        service="deploy-service",
        client_ip=request.client.host if request.client else None,
    )

    try:
        signature = request.headers.get("X-Hub-Signature-256")

        if not verify_signature(body, signature):
            log.warning("Неверная подпись webhook")
            await send_tg("❌ DeployService: неверная подпись webhook")
            raise HTTPException(403)

        event = request.headers.get("X-GitHub-Event")

        set_context(github_event=event)

        log.info("Получен webhook")

        if event == "ping":
            log.info("Ping от GitHub")
            return {"status": "pong"}

        if event != "push":
            log.info("Событие проигнорировано")
            return {"status": "ignored"}

        payload = await request.json()

        ref = payload.get("ref")
        repo = payload.get("repository", {}).get("name")

        set_context(repo=repo, ref=ref)

        log.info("Webhook push обработка")

        if ref != "refs/heads/main":
            log.info("Не main ветка — деплой пропущен")
            return {"status": "ignored"}

        if not repo:
            log.error("Имя репозитория отсутствует")
            await send_tg("❌ DeployService: repo не найден")
            raise HTTPException(400)

        project_dir = Path(PROJECTS_ROOT) / repo
        deploy_script = project_dir / "deploy.sh"

        if not deploy_script.exists():
            log.error(
                "deploy.sh не найден",
                extra={"deploy_path": str(deploy_script)},
            )

            await send_tg(
                f"❌ <b>DEPLOY FAILED</b>\n"
                f"Проект: {repo}\n"
                f"deploy.sh не найден"
            )

            raise HTTPException(404)

        log.info(
            "Запуск deploy.sh",
            extra={"deploy_path": str(deploy_script)},
        )

        def stream_logs(proc):
            for line in proc.stdout:
                log.info(f"[deploy] {line.strip()}")

            exit_code = proc.wait()
            log.info(f"Deploy завершён (exit_code={exit_code})")

        proc = subprocess.Popen(
            [str(deploy_script)],
            cwd=str(project_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        threading.Thread(
            target=stream_logs,
            args=(proc,),
            daemon=True,
        ).start()

        log.info("Deploy успешно запущен")

        return {"status": "deploy started", "repo": repo}

    except Exception:
        log.exception("Ошибка обработки webhook")
        raise

    finally:
        # ОБЯЗАТЕЛЬНО — очистка contextvars
        clear_context()
