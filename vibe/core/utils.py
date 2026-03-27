from __future__ import annotations

import random
import re
import string
from pathlib import Path
from urllib.parse import urlparse

import aiohttp


def safe_filename_from_url(url: str, fallback: str = "module.py") -> str:
    parsed = urlparse(url)
    candidate = Path(parsed.path).name or fallback
    return candidate if candidate.endswith(".py") else f"{candidate}.py"


def random_bot_username(prefix: str = "vibe") -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}_{suffix}_bot"


def extract_bot_token(text: str) -> str | None:
    match = re.search(r"(\d{6,}:[A-Za-z0-9_-]{20,})", text)
    return match.group(1) if match else None


async def download_text(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
            response.raise_for_status()
            return await response.text()
