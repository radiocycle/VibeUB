from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InlineQuery, Message

from vibe.core.context import InlineQueryContext

LOGGER = logging.getLogger(__name__)


class InlineManager:
    def __init__(self, app: Any) -> None:
        self.app = app
        self._bot: Bot | None = None
        self._dispatcher: Dispatcher | None = None
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        config = self.app.config.inline
        if not (config.is_enabled and config.bot_token):
            LOGGER.info("Inline bot is not configured; skipping startup")
            return

        self._bot = Bot(
            token=config.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self._dispatcher = Dispatcher()
        router = Router()

        @router.inline_query()
        async def on_inline_query(query: InlineQuery) -> None:
            await self._handle_inline_query(query)

        @router.callback_query()
        async def on_callback(query: CallbackQuery) -> None:
            await self._handle_callback(query)

        @router.message(CommandStart())
        async def on_start(message: Message) -> None:
            await self._handle_start(message)

        self._dispatcher.include_router(router)
        self._task = asyncio.create_task(
            self._dispatcher.start_polling(self._bot, handle_signals=False)
        )

    async def stop(self) -> None:
        if self._dispatcher is not None:
            with contextlib.suppress(RuntimeError):
                await self._dispatcher.stop_polling()
        if self._bot is not None:
            await self._bot.session.close()
        if self._task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._dispatcher = None
        self._bot = None
        self._task = None

    async def restart(self) -> None:
        if self.is_running:
            await self.stop()
        await self.start()

    async def _handle_inline_query(self, query: InlineQuery) -> None:
        text = (query.query or "").strip()
        command_name, _, _ = text.partition(" ")
        ctx = InlineQueryContext(app=self.app, query=query)
        if command_name and command_name in self.app.modules.inline_handlers:
            handler = self.app.modules.inline_handlers[command_name]
            results = await handler.callback(ctx)
        else:
            results = await self._default_results(ctx)
        await query.answer(results=results, cache_time=1, is_personal=True)

    async def _default_results(self, ctx: InlineQueryContext) -> list[Any]:
        prefix = self.app.config.prefix
        commands = ", ".join(cmd.name for cmd in self.app.modules.list_primary_commands())
        return [
            ctx.article(
                title="Vibe Inline",
                description="Runtime status and available commands",
                message_text=(
                    "<b>Vibe Inline</b>\n"
                    f"Prefix: <code>{prefix}</code>\n"
                    f"Commands: <code>{commands}</code>"
                ),
            )
        ]

    async def _handle_start(self, message: Message) -> None:
        prefix = self.app.config.prefix
        inline_username = self.app.config.inline.bot_username or "not configured"
        text = (
            "<b>Vibe Inline Bot</b>\n"
            "Inline mode is ready.\n\n"
            f"Bot: <code>{inline_username}</code>\n"
            f"Prefix: <code>{prefix}</code>\n"
            "Use the bot inline in any chat and call <code>config</code> or <code>info</code>."
        )
        await message.answer(text)

    async def _handle_callback(self, query: CallbackQuery) -> None:
        data = query.data or ""
        if not data.startswith("cfg:"):
            await query.answer()
            return

        config_module = self.app.modules.get_module("config")
        if config_module is None:
            await query.answer("Config module is not loaded.", show_alert=True)
            return

        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        if action == "root":
            await query.message.edit_text(
                "Vibe config panel",
                reply_markup=config_module._modules_keyboard(),
            )
            await query.answer()
            return
        if action == "module" and len(parts) == 3:
            module_name = parts[2]
            module = self.app.modules.modules.get(module_name)
            if module is None:
                await query.answer("Module not found.", show_alert=True)
                return
            keyboard = config_module.build_module_keyboard(module_name)
            await query.message.edit_text(
                f"{module.title} ({module.name})\n{module.description}",
                reply_markup=keyboard,
            )
            await query.answer()
            return
        if action == "option" and len(parts) == 4:
            module_name = parts[2]
            option_key = parts[3]
            module = self.app.modules.modules.get(module_name)
            if module is None:
                await query.answer("Module not found.", show_alert=True)
                return
            option = next((item for item in module.get_options() if item.key == option_key), None)
            if option is None:
                await query.answer("Option not found.", show_alert=True)
                return
            await query.answer(f"{option.label}: {option.value}\n{option.description}", show_alert=True)
            return
        if action == "none":
            await query.answer("No modules available.", show_alert=True)
            return
        await query.answer()
