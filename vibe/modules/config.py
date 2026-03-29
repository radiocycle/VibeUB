import asyncio
import html
import secrets
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import BotResponseTimeout

from vibe.core import BaseModule, ModuleOption, command, inline_handler


class ConfigModule(BaseModule):
    name = "config"
    title = "Config"
    description = "Configuration management."

    @command("config", help_text="Show config summary and inline config panel.")
    async def config_command(self, ctx) -> None:
        if not ctx.args:
            if not await self._open_inline_panel(ctx, "config"):
                await ctx.reply(
                    "⚠️ <b>Config Panel</b>\n"
                    "Inline menu could not be opened right now.\n"
                    "Check <code>inline status</code> or restart inline."
                )
                return
            await ctx.edit(ctx.app.i18n.text("config_panel_opened"))
            return

        action = ctx.args[0].lower()
        if action == "get" and len(ctx.args) == 2:
            key = ctx.args[1]
            if "." in key:
                module_name, option_key = key.split(".", 1)
                value = ctx.app.config_manager.get_module_option(module_name, option_key)
            else:
                value = getattr(ctx.app.config, key, None)
            await ctx.reply(f"<b>⚙️ Config Value</b>\n<code>{key}</code> = <code>{value}</code>")
            return

        if action == "set" and len(ctx.args) >= 3:
            key = ctx.args[1]
            value = " ".join(ctx.args[2:])
            if key == "prefix":
                ctx.app.config_manager.set_prefix(value)
                ctx.app.config.prefix = value
                await ctx.reply(f"<b>✅ Config Updated</b>\nPrefix: <code>{value}</code>")
                return
            if "." in key:
                module_name, option_key = key.split(".", 1)
                option = self.get_module_option(module_name, option_key)
                if option is None:
                    await ctx.reply(f"<b>❌ Config Option Not Found</b>\n<code>{key}</code>")
                    return
                is_valid, parsed_value, error = self.validate_option_value(option, value)
                if not is_valid:
                    await ctx.reply(
                        "<b>❌ Invalid Config Value</b>\n"
                        f"Key: <code>{key}</code>\n"
                        f"Type: <code>{option.value_type}</code>\n"
                        f"Error: <code>{html.escape(error or 'unknown error')}</code>"
                    )
                    return
                ctx.app.config_manager.set_module_option(module_name, option_key, parsed_value)
                await ctx.reply(
                    "<b>✅ Config Updated</b>\n"
                    f"Key: <code>{key}</code>\n"
                    f"Value: <code>{html.escape(str(parsed_value))}</code>"
                )
                return
            await ctx.reply("<b>⚙️ Config</b>\nOnly <code>prefix</code> can be updated through this command right now.")
            return

        await ctx.reply(
            "<b>⚙️ Config</b>\n"
            "Usage:\n"
            "<code>config</code>\n"
            "<code>config get &lt;key&gt;</code>\n"
            "<code>config set prefix &lt;value&gt;</code>\n"
            "<code>config get info.template</code>\n"
            "<code>config set ping.result_template &lt;value&gt;</code>"
        )

    @command("setlanguage", help_text="Open language selection menu.")
    async def setlanguage(self, ctx) -> None:
        if not await self._open_inline_panel(ctx, "language"):
            await ctx.reply(
                "⚠️ <b>Language Menu</b>\n"
                "Inline menu could not be opened right now.\n"
                "Check <code>inline status</code> or restart inline."
            )
            return
        await ctx.edit(ctx.app.i18n.text("setlanguage_opened"))

    @inline_handler("config", description="Show config panel")
    async def config_inline(self, query):
        keyboard = self._root_keyboard()
        return [
            query.article(
                title="⚙️ Vibe config",
                description="Open module options",
                message_text=query.app.i18n.text("config_panel_title"),
                reply_markup=keyboard,
            )
        ]

    @inline_handler("language", description="Open language menu")
    async def language_inline(self, query):
        return [
            query.article(
                title=query.app.i18n.text("language_article_title"),
                description=query.app.i18n.text("language_article_description"),
                message_text=query.app.i18n.text("language_article_text"),
                reply_markup=self._language_keyboard(),
            )
        ]

    def _root_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=self.app.i18n.text("config_category_core"), callback_data="cfg:category:core"),
                    InlineKeyboardButton(text=self.app.i18n.text("config_category_external"), callback_data="cfg:category:external"),
                ],
                [
                    InlineKeyboardButton(text=self.app.i18n.text("config_category_language"), callback_data="cfg:language"),
                ],
            ]
        )

    def _category_keyboard(self, category: str) -> InlineKeyboardMarkup:
        modules = [
            module
            for module in sorted(self.app.modules.modules.values(), key=lambda item: item.title.lower())
            if self.app.modules.is_core_module(module.name) == (category == "core")
        ]
        rows: list[list[InlineKeyboardButton]] = []
        current_row: list[InlineKeyboardButton] = []
        for module in modules:
            current_row.append(InlineKeyboardButton(text=module.title, callback_data=f"cfg:module:{module.name}"))
            if len(current_row) == 2:
                rows.append(current_row)
                current_row = []
        if current_row:
            rows.append(current_row)
        if not rows:
            label = self.app.i18n.text("config_no_modules_core" if category == "core" else "config_no_modules_external")
            rows = [[InlineKeyboardButton(text=label, callback_data="cfg:none")]]
        rows.append([InlineKeyboardButton(text=self.app.i18n.text("config_back"), callback_data="cfg:root")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def build_module_keyboard(self, module_name: str) -> InlineKeyboardMarkup:
        module = self.app.modules.modules[module_name]
        rows = []
        current_row = []
        for option in module.get_options():
            current_row.append(
                InlineKeyboardButton(
                    text=option.label,
                    callback_data=f"cfg:option:{module.name}:{option.key}",
                )
            )
            if len(current_row) == 2:
                rows.append(current_row)
                current_row = []
        if current_row:
            rows.append(current_row)
        back_target = "core" if self.app.modules.is_core_module(module_name) else "external"
        rows.append([InlineKeyboardButton(text=self.app.i18n.text("config_back"), callback_data=f"cfg:category:{back_target}")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def build_option_keyboard(self, module_name: str, option_key: str) -> InlineKeyboardMarkup:
        rows: list[list[InlineKeyboardButton]] = []
        option = self.get_module_option(module_name, option_key)
        if option is not None and option.editable:
            if option.value_type == "boolean":
                rows.append(
                    [
                        InlineKeyboardButton(text="✅ True", callback_data=f"cfg:set:{module_name}:{option_key}:true"),
                        InlineKeyboardButton(text="❌ False", callback_data=f"cfg:set:{module_name}:{option_key}:false"),
                    ]
                )
            elif option.value_type == "choice" and option.choices:
                current_row: list[InlineKeyboardButton] = []
                for choice in option.choices:
                    current_row.append(
                        InlineKeyboardButton(
                            text=choice,
                            callback_data=f"cfg:set:{module_name}:{option_key}:{choice}",
                        )
                    )
                    if len(current_row) == 2:
                        rows.append(current_row)
                        current_row = []
                if current_row:
                    rows.append(current_row)
            else:
                token = self._create_edit_token(module_name, option_key)
                rows.append(
                    [
                        InlineKeyboardButton(
                            text="✏️ Change",
                            switch_inline_query_current_chat=f"{token} ",
                        )
                    ]
                )
        if option is not None and option.default is not None:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="♻️ Restore Default",
                        callback_data=f"cfg:reset:{module_name}:{option_key}",
                    )
                ]
            )
        rows.append([InlineKeyboardButton(text=self.app.i18n.text("config_back"), callback_data=f"cfg:module:{module_name}")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def get_module_option(self, module_name: str, option_key: str) -> ModuleOption | None:
        module = self.app.modules.modules.get(module_name)
        if module is None:
            return None
        return next((item for item in module.get_options() if item.key == option_key), None)

    def render_option_text(self, module_name: str, option: ModuleOption) -> str:
        value = option.value
        if value is None or value == "":
            value = "not set"
        lines = [
            f"⚙️ <b>{html.escape(option.label)}</b>",
            f"📦 Module: <code>{html.escape(module_name)}</code>",
            f"🗝 Key: <code>{html.escape(option.key)}</code>",
            f"💾 Current Value:\n<blockquote expandable><code>{html.escape(str(value))}</code></blockquote>",
            f"📝 Description:\n{option.description}",
        ]
        if option.default is not None:
            default_value = option.default
            if default_value == "":
                default_value = "empty"
            lines.append(
                f"♻️ Default Value:\n<blockquote expandable><code>{html.escape(str(default_value))}</code></blockquote>"
            )
        if option.placeholders:
            placeholders = "\n".join(
                f"• <code>{html.escape(name)}</code> - {html.escape(description)}"
                for name, description in option.placeholders
            )
            lines.append(f"🧩 Placeholders:\n<blockquote expandable>{placeholders}</blockquote>")
        else:
            lines.append("🧩 Placeholders:\n<blockquote expandable>No placeholders available.</blockquote>")
        lines.append(f"🧷 Type: <code>{html.escape(option.value_type)}</code>")
        if option.value_type == "choice" and option.choices:
            choices = ", ".join(f"<code>{html.escape(choice)}</code>" for choice in option.choices)
            lines.append(f"🎛 Choices: {choices}")
        if option.editable:
            lines.append("✏️ Use the button below to change this value.")
        return "\n".join(lines)

    def validate_option_value(self, option: ModuleOption, raw_value: str) -> tuple[bool, Any, str | None]:
        value = raw_value.strip()
        if option.value_type == "string":
            return True, value, None
        if option.value_type == "boolean":
            lowered = value.lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True, True, None
            if lowered in {"0", "false", "no", "off"}:
                return True, False, None
            return False, None, "Expected boolean value: true/false"
        if option.value_type == "integer":
            try:
                return True, int(value), None
            except ValueError:
                return False, None, "Expected integer value"
        if option.value_type == "float":
            try:
                return True, float(value), None
            except ValueError:
                return False, None, "Expected float value"
        if option.value_type == "choice":
            if value in option.choices:
                return True, value, None
            return False, None, f"Expected one of: {', '.join(option.choices)}"
        return False, None, f"Unsupported config type: {option.value_type}"

    def _language_keyboard(self) -> InlineKeyboardMarkup:
        rows = [
            [
                InlineKeyboardButton(text="🇺🇸 English", callback_data="cfg:setlang:en"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="cfg:setlang:ru"),
            ],
            [InlineKeyboardButton(text=self.app.i18n.text("config_back"), callback_data="cfg:root")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def get_options(self) -> list[ModuleOption]:
        return [
            ModuleOption(key="prefix", label="Prefix", description="Command prefix", value=self.app.config.prefix),
            ModuleOption(
                key="inline_bot",
                label="Inline",
                description="Inline bot username",
                value=self.app.config.inline.bot_username or "disabled",
            ),
            ModuleOption(
                key="language",
                label="Language",
                description="Current UI language",
                value=self.app.config.language,
            ),
        ]

    async def _open_inline_panel(self, ctx, query_text: str) -> bool:
        inline_username = ctx.app.config.inline.bot_username
        if not inline_username:
            return False
        if not ctx.app.inline.is_running:
            await ctx.app.inline.restart()
            await asyncio.sleep(1.0)

        for _ in range(2):
            try:
                results = await ctx.client.get_inline_bot_results(inline_username, query_text)
                if not getattr(results, "results", None):
                    return False
                await ctx.client.send_inline_bot_result(
                    chat_id=ctx.message.chat.id,
                    query_id=results.query_id,
                    result_id=results.results[0].id,
                    reply_to_message_id=getattr(ctx.message, "reply_to_message_id", None),
                )
                return True
            except BotResponseTimeout:
                await ctx.app.inline.restart()
                await asyncio.sleep(1.0)
        return False

    def build_edit_inline_results(self, query) -> list | None:
        text = ((query.query.query or "") if hasattr(query.query, "query") else (query.query or "")).strip()
        if not text:
            return None

        token, _, value = text.partition(" ")
        target = self._get_edit_target(token)
        if target is None:
            return None

        module_name, option_key = target
        option = self.get_module_option(module_name, option_key)
        if option is None:
            return [
                query.article(
                    title="❌ Config Option Not Found",
                    description=f"{module_name}.{option_key}",
                    message_text=(
                        "<b>❌ Config Option Not Found</b>\n"
                        f"Target: <code>{module_name}.{option_key}</code>"
                    ),
                )
            ]
        value = value.strip()
        if not value:
            return [
                query.article(
                    title="✏️ Config Edit",
                    description=f"Type a new value for {module_name}.{option_key}",
                    message_text=(
                        "<b>✏️ Config Edit</b>\n"
                        f"Target: <code>{module_name}.{option_key}</code>\n"
                        f"Type: <code>{option.value_type}</code>\n"
                        "Type a value after the token and choose this result again."
                    ),
                )
            ]

        is_valid, parsed_value, error = self.validate_option_value(option, value)
        if not is_valid:
            return [
                query.article(
                    title="❌ Invalid Config Value",
                    description=error or f"{module_name}.{option_key}",
                    message_text=(
                        "<b>❌ Invalid Config Value</b>\n"
                        f"Target: <code>{module_name}.{option_key}</code>\n"
                        f"Type: <code>{option.value_type}</code>\n"
                        f"Error: <code>{html.escape(error or 'unknown error')}</code>"
                    ),
                )
            ]

        result_id = f"cfgedit:{secrets.token_hex(8)}"
        self.app.config_manager.set_module_option(module_name, option_key, parsed_value)
        applied = self.storage.setdefault("applied_edit_results", set())
        applied.add(result_id)
        return [
            query.article(
                title="✅ Save Config Value",
                description=f"{module_name}.{option_key} = {str(parsed_value)[:32]}",
                message_text=(
                    "<b>✅ Config Value Saved</b>\n"
                    f"Target: <code>{module_name}.{option_key}</code>\n"
                    f"Value: <code>{html.escape(str(parsed_value))}</code>"
                ),
                id_=result_id,
            )
        ]

    def apply_inline_result(self, result_id: str) -> bool:
        applied = self.storage.setdefault("applied_edit_results", set())
        return result_id in applied

    def _create_edit_token(self, module_name: str, option_key: str) -> str:
        tokens = self.storage.setdefault("edit_tokens", {})
        token = f"id{secrets.token_hex(4)}"
        tokens[token] = (module_name, option_key)
        return token

    def _get_edit_target(self, token: str):
        return self.storage.setdefault("edit_tokens", {}).get(token)


module = ConfigModule()
