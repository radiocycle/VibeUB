from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, ChosenInlineResult, InlineKeyboardButton, InlineKeyboardMarkup, InlineQuery, Message

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

        @router.chosen_inline_result()
        async def on_chosen_inline_result(result: ChosenInlineResult) -> None:
            await self._handle_chosen_inline_result(result)

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
        config_module = self.app.modules.get_module("config")
        if config_module is not None:
            custom_results = config_module.build_edit_inline_results(ctx)
            if custom_results is not None:
                await query.answer(results=custom_results, cache_time=1, is_personal=True)
                return
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
                title=ctx.app.i18n.text("inline_default_title"),
                description=ctx.app.i18n.text("inline_default_description"),
                message_text=ctx.app.i18n.text(
                    "inline_default_text",
                    prefix=prefix,
                    commands=commands,
                ),
            )
        ]

    async def _handle_start(self, message: Message) -> None:
        prefix = self.app.config.prefix
        inline_username = self.app.config.inline.bot_username or "not configured"
        text = self.app.i18n.text(
            "inline_start",
            inline_username=inline_username,
            prefix=prefix,
        )
        await message.answer(text)

    async def _handle_chosen_inline_result(self, result: ChosenInlineResult) -> None:
        config_module = self.app.modules.get_module("config")
        if config_module is None:
            return
        config_module.apply_inline_result(result.result_id)

    async def _handle_callback(self, query: CallbackQuery) -> None:
        data = query.data or ""
        if not data.startswith("cfg:"):
            await query.answer()
            return

        config_module = self.app.modules.get_module("config")
        if config_module is None:
            await query.answer("⚠️ Config module is not loaded.", show_alert=True)
            return

        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        if action == "root":
            await self._edit_callback_message(
                query,
                text=self.app.i18n.text("config_panel_title"),
                reply_markup=config_module._root_keyboard(),
            )
            await query.answer()
            return
        if action == "category" and len(parts) == 3:
            category = parts[2]
            await self._edit_callback_message(
                query,
                text=self.app.i18n.text("config_panel_title"),
                reply_markup=config_module._category_keyboard(category),
            )
            await query.answer()
            return
        if action == "language":
            await self._edit_callback_message(
                query,
                text=self.app.i18n.text("config_language_title", language=self.app.config.language),
                reply_markup=config_module._language_keyboard(),
            )
            await query.answer()
            return
        if action == "setlang" and len(parts) == 3:
            language = parts[2]
            if language not in {"en", "ru"}:
                await query.answer("❌ Language not found.", show_alert=True)
                return
            self.app.config_manager.set_language(language)
            self.app.config.language = language
            await self._edit_callback_message(
                query,
                text=self.app.i18n.text("config_language_title", language=self.app.config.language),
                reply_markup=config_module._language_keyboard(),
            )
            await query.answer(self.app.i18n.text("config_language_saved", language=language), show_alert=True)
            return
        if action == "module" and len(parts) == 3:
            module_name = parts[2]
            module = self.app.modules.modules.get(module_name)
            if module is None:
                await query.answer(self.app.i18n.text("config_module_not_found"), show_alert=True)
                return
            keyboard = config_module.build_module_keyboard(module_name)
            await self._edit_callback_message(
                query,
                text=self.app.i18n.text(
                    "config_module_title",
                    title=module.title,
                    name=module.name,
                    description=module.description,
                ),
                reply_markup=keyboard,
            )
            await query.answer()
            return
        if action == "option" and len(parts) == 4:
            module_name = parts[2]
            option_key = parts[3]
            module = self.app.modules.modules.get(module_name)
            if module is None:
                await query.answer(self.app.i18n.text("config_module_not_found"), show_alert=True)
                return
            option = config_module.get_module_option(module_name, option_key)
            if option is None:
                await query.answer(self.app.i18n.text("config_option_not_found"), show_alert=True)
                return
            await self._edit_callback_message(
                query,
                text=config_module.render_option_text(module_name, option),
                reply_markup=config_module.build_option_keyboard(module_name, option_key),
            )
            await query.answer()
            return
        if action == "set" and len(parts) >= 5:
            module_name = parts[2]
            option_key = parts[3]
            raw_value = ":".join(parts[4:])
            option = config_module.get_module_option(module_name, option_key)
            if option is None:
                await query.answer(self.app.i18n.text("config_option_not_found"), show_alert=True)
                return
            is_valid, parsed_value, error = config_module.validate_option_value(option, raw_value)
            if not is_valid:
                await query.answer(error or "Invalid value.", show_alert=True)
                return
            self.app.config_manager.set_module_option(module_name, option_key, parsed_value)
            refreshed_option = config_module.get_module_option(module_name, option_key)
            if refreshed_option is None:
                await query.answer(self.app.i18n.text("config_option_not_found"), show_alert=True)
                return
            await self._edit_callback_message(
                query,
                text=config_module.render_option_text(module_name, refreshed_option),
                reply_markup=config_module.build_option_keyboard(module_name, option_key),
            )
            await query.answer(f"✅ {option.label}: {parsed_value}", show_alert=True)
            return
        if action == "none":
            await query.answer("📭", show_alert=True)
            return
        await query.answer()

    async def _edit_callback_message(
        self,
        query: CallbackQuery,
        *,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        if query.message is not None:
            await query.message.edit_text(text, reply_markup=reply_markup)
            return

        inline_message_id = query.inline_message_id
        if inline_message_id is None or self._bot is None:
            raise RuntimeError("No editable message target in callback query.")

        await self._bot.edit_message_text(
            text=text,
            inline_message_id=inline_message_id,
            reply_markup=reply_markup,
        )
