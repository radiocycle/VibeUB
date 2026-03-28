from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import os
import signal
import sqlite3
import sys
from time import perf_counter
from typing import Any

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler

from vibe.bootstrap import ensure_api_credentials, ensure_not_root
from vibe.config import AppConfig, ConfigManager
from vibe.core.botfather import BotFatherService
from vibe.core.context import CommandContext
from vibe.core.inline import InlineManager
from vibe.core.loader import ModuleManager
from vibe.i18n import Localizer
from vibe.logging import setup_logging

LOGGER = logging.getLogger(__name__)


class VibeUB:
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        self.config: AppConfig = config_manager.config
        self.client = Client(
            name=self.config.session_name,
            api_id=self.config.api_id,
            api_hash=self.config.api_hash,
            workdir=str(self.config.resolved_workdir),
            in_memory=False,
        )
        self.modules = ModuleManager(self)
        self.inline = InlineManager(self)
        self.botfather = BotFatherService(self.client)
        self.i18n = Localizer(self)
        self.started_at = perf_counter()
        self.me: Any = None
        self._restart_requested = False
        self._shutdown_event = asyncio.Event()
        self._stopping = False

    async def start(self) -> None:
        self._prepare_session_file()
        try:
            await self.client.start()
        except sqlite3.OperationalError as exc:
            if "no such table: version" not in str(exc).lower():
                raise
            self._reset_broken_session_file()
            await self.client.start()
        self.me = await self.client.get_me()
        await self.modules.load_all()
        self.client.add_handler(MessageHandler(self._message_router, filters.me & filters.text))
        await self.inline.start()
        LOGGER.info("VibeUB started as @%s", getattr(self.me, "username", "unknown"))

    async def run_forever(self) -> None:
        await self.start()
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        if self._stopping:
            return
        self._stopping = True
        self._shutdown_event.set()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(self.inline.stop(), timeout=5)
        with contextlib.suppress(ConnectionError, RuntimeError, asyncio.TimeoutError):
            await asyncio.wait_for(self.client.stop(block=False), timeout=5)
        if self._restart_requested:
            os.execv(sys.executable, [sys.executable, "-m", "vibe"])

    def request_restart(self) -> None:
        self._restart_requested = True

    def request_shutdown(self) -> None:
        self._shutdown_event.set()

    def _session_path(self) -> str:
        return str(self.config.resolved_workdir / f"{self.config.session_name}.session")

    def _prepare_session_file(self) -> None:
        path = self._session_path()
        if not os.path.exists(path):
            return
        with open(path, "rb") as handle:
            header = handle.read(16)
        if header != b"SQLite format 3\x00":
            os.remove(path)

    def _reset_broken_session_file(self) -> None:
        path = self._session_path()
        if os.path.exists(path):
            os.remove(path)

    async def _message_router(self, client: Client, message: Any) -> None:
        text = getattr(message, "text", None) or ""
        prefix = self.config.prefix
        if not text.startswith(prefix):
            return

        without_prefix = text[len(prefix):].strip()
        if not without_prefix:
            return
        command_name, _, raw_args = without_prefix.partition(" ")
        alias_expansion = self.config.aliases.get(command_name.lower())
        if alias_expansion:
            expanded = alias_expansion.strip()
            if raw_args:
                expanded = f"{expanded} {raw_args}".strip()
            command_name, _, raw_args = expanded.partition(" ")
        lookup_name = command_name.lower()
        command = self.modules.commands.get(lookup_name)
        if command is None:
            return
        ctx = CommandContext(
            app=self,
            message=message,
            command=command.name,
            args=raw_args.split() if raw_args else [],
            raw_args=raw_args.strip(),
            prefix=prefix,
            started_at=perf_counter(),
        )
        try:
            await command.callback(ctx)
        except Exception as exc:
            LOGGER.exception("Command %s failed", command.name)
            await ctx.reply(
                "<b>❌ Command Failed</b>\n"
                f"Command: <code>{command.name}</code>\n"
                f"Error: <code>{type(exc).__name__}: {exc}</code>"
            )


def cli() -> None:
    parser = argparse.ArgumentParser(description="Run VibeUB userbot")
    parser.add_argument("--bot-token", dest="bot_token", default=None, help="Use an existing inline bot token")
    parser.add_argument("--root", action="store_true", help="Allow running as root user")
    args = parser.parse_args()
    asyncio.run(_main(args))


async def _main(args: argparse.Namespace) -> None:
    ensure_not_root(args.root)
    config_manager = ConfigManager.load(bot_token=args.bot_token)
    ensure_api_credentials(config_manager)
    setup_logging(config_manager.config.log_level, config_manager.config.resolved_log_file)
    app = VibeUB(config_manager)
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, app.request_shutdown)

    try:
        await app.run_forever()
    except (KeyboardInterrupt, asyncio.CancelledError):
        LOGGER.info("Shutdown signal received")
    finally:
        await app.stop()
