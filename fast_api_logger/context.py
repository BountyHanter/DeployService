from __future__ import annotations

"""
Контекст логирования (contextvars).

ЗАЧЕМ ЭТОТ ФАЙЛ:
- Хранит контекст логов, автоматически подмешиваемый в каждый лог.
- Избавляет от постоянной передачи request_id / trace_id через extra.
- Безопасен для async / await / streaming.

КАК ИСПОЛЬЗОВАТЬ:
- set_context(...)        — положить произвольные поля
- remove_context(...)     — удалить поля
- clear_context()         — очистить всё
- set_request_id(...)     — удобный хелпер для частого кейса

РАСШИРЕНИЕ:
- Ниже есть раздел "CUSTOM HELPERS".
- Ты можешь добавлять туда любые set_* функции под свои нужды.
"""

from contextvars import ContextVar
from typing import Any, Dict, Optional

# ============================================================
# ОСНОВНОЙ КОНТЕКСТ ЛОГОВ
# ============================================================
#
# Здесь хранится словарь кастомных полей логирования.
#
# ВАЖНЫЕ ПРАВИЛА:
# - Значения должны быть простыми (str/int/bool/float).
# - НЕ класть тяжёлые объекты (Request, Thread, Run и т.п.).
# - Контекст изолирован на coroutine (contextvars).
#

_log_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "log_context",
    default=None
)


# ============================================================
# STREAM-SAFE ФЛАГ
# ============================================================
#
# Используется логгером, чтобы:
# - не писать в stdout во время StreamingResponse / SSE
# - избежать тихих обрывов стрима
#

_streaming: ContextVar[bool] = ContextVar(
    "streaming",
    default=False
)


# ============================================================
# БАЗОВЫЕ API ФУНКЦИИ (НЕ МЕНЯТЬ СИГНАТУРЫ)
# ============================================================

def get_context() -> dict[str, Any]:
    """
    Возвращает копию текущего контекста логирования.
    """
    ctx = _log_context.get()
    return dict(ctx) if ctx else {}


def set_context(**kwargs: Any) -> None:
    """
    Обновляет контекст (merge):
    - добавляет новые ключи
    - перезаписывает существующие
    - None-значения игнорируются
    """
    ctx = get_context()
    for k, v in kwargs.items():
        if v is None:
            continue
        ctx[k] = v
    _log_context.set(ctx)


def set_context_dict(data: dict[str, Any]) -> None:
    """
    Полностью заменяет контекст указанным словарём.
    """
    _log_context.set(dict(data) if data else {})


def remove_context(*keys: str) -> None:
    """
    Удаляет указанные ключи из контекста.
    """
    if not keys:
        return
    ctx = get_context()
    for k in keys:
        ctx.pop(k, None)
    _log_context.set(ctx)


def clear_context() -> None:
    """
    Полностью очищает контекст.
    """
    _log_context.set({})


# ============================================================
# CUSTOM HELPERS (МОЖНО И НУЖНО РАСШИРЯТЬ)
# ============================================================
#
# Ниже — удобные хелперы для частых кейсов.
# Ты можешь добавлять сюда свои функции:
#
#   - set_user_id(user_id)
#   - set_chat_id(chat_id)
#   - set_trace_id(trace_id)
#   - set_session_id(session_id)
#
# Главное правило:
#   Хелпер = тонкая обёртка над set_context / remove_context
#

def set_request_id(request_id: str | None) -> None:
    """
    Кладёт request_id в контекст.
    Если None — удаляет request_id.
    """
    if request_id is None:
        remove_context("request_id")
    else:
        set_context(request_id=request_id)

def get_request_id() -> str | None:
    return get_context().get("request_id")

def get_base_profile_id() -> int | None:
    return get_context().get("base_profile_id")

# Пример для будущего (НЕ ОБЯЗАТЕЛЬНО):
#
# def set_user_id(user_id: int | None) -> None:
#     if user_id is None:
#         remove_context("user_id")
#     else:
#         set_context(user_id=user_id)


# ============================================================
# STREAM-SAFE API
# ============================================================

def set_streaming(is_streaming: bool) -> None:
    """
    Сообщает логгеру, что сейчас идёт стрим.
    Используется для STREAM_SAFE режима.
    """
    _streaming.set(bool(is_streaming))


def is_streaming() -> bool:
    """
    Возвращает True, если сейчас идёт стрим.
    """
    return _streaming.get()
