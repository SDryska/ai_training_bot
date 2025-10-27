from __future__ import annotations

from typing import Dict, Optional
from urllib.parse import quote, unquote

# Простой и компактный пакер/распаковщик callback-данных.
# Формат: "<префикс>|k1=v1;k2=v2". Общая длина <= 64 байта для Telegram.
# Ключи отсортированы для стабильного вывода.


def pack(data: Dict[str, str] | None = None, prefix: Optional[str] = None) -> str:
    parts: list[str] = []
    if prefix:
        parts.append(prefix)
    if data:
        items = [f"{quote(str(k))}={quote(str(v))}" for k, v in sorted(data.items())]
        parts.append(";".join(items))
    return "|".join(parts)


def unpack(cb: str) -> tuple[Optional[str], Dict[str, str]]:
    prefix: Optional[str] = None
    payload = {}
    if "|" in cb:
        prefix, rest = cb.split("|", 1)
    else:
        # Нет префикса, вся строка - это payload
        rest = cb
    if rest:
        for pair in rest.split(";"):
            if not pair:
                continue
            if "=" not in pair:
                continue
            k, v = pair.split("=", 1)
            payload[unquote(k)] = unquote(v)
    return prefix, payload
