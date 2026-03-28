from __future__ import annotations

import os
import re
import sys
from getpass import getpass


def ensure_not_root(allow_root: bool) -> None:
    geteuid = getattr(os, "geteuid", None)
    if geteuid is None:
        return
    if geteuid() == 0 and not allow_root:
        raise RuntimeError("⛔ Root execution is blocked. Start with `--root` to allow it.")


def ensure_api_credentials(config_manager) -> None:
    config = config_manager.config
    if _is_valid_api_credentials(config.api_id, config.api_hash):
        return
    if not sys.stdin.isatty():
        raise RuntimeError("⚠️ API credentials are missing in config.json and interactive input is unavailable.")

    print("\n" + "=" * 44)
    print(" " * 13 + "✨ VIBE SETUP")
    print("=" * 44)
    print("🔑 Enter Telegram API credentials from my.telegram.org\n")
    if config.api_id or config.api_hash:
        print("⚠️ Stored credentials are invalid. Enter a real api_id/api_hash pair.\n")

    while True:
        api_id_raw = input("API ID   > ").strip()
        if api_id_raw.isdigit():
            api_id = int(api_id_raw)
            break
        print("❌ API ID must be a number.\n")

    while True:
        api_hash = getpass("API HASH > ").strip()
        if _is_valid_api_hash(api_hash):
            break
        print("❌ API HASH must be a 32-character hex string.\n")

    print("\n✅ Saved credentials to config.json\n")
    config_manager.set_api_credentials(api_id=api_id, api_hash=api_hash)


def _is_valid_api_hash(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{32}", value or ""))


def _is_valid_api_credentials(api_id: int, api_hash: str) -> bool:
    return api_id > 0 and _is_valid_api_hash(api_hash)
