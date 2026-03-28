import asyncio

from vibe.core.botfather import BotFatherRateLimitError
from vibe.core import BaseModule, command


class InlineModule(BaseModule):
    name = "inline"
    title = "Inline"
    description = "Inline bot management."

    @command("inline", help_text="Manage inline bot: inline setup | status | restart")
    async def inline_command(self, ctx) -> None:
        if not ctx.args:
            await ctx.reply(
                "<b>🤖 Inline Control</b>\n"
                "Commands:\n"
                "<code>inline setup</code>\n"
                "<code>inline status</code>\n"
                "<code>inline restart</code>"
            )
            return

        action = ctx.args[0].lower()
        if action == "status":
            config = ctx.app.config.inline
            await ctx.reply(
                "\n".join(
                    [
                        "<b>🤖 Inline Status</b>",
                        f"Enabled: <code>{config.is_enabled}</code>",
                        f"Username: <code>{config.bot_username or 'not configured'}</code>",
                        f"Running: <code>{ctx.app.inline.is_running}</code>",
                    ]
                )
            )
            return

        if action == "setup":
            await ctx.reply("<b>🛠 Inline Setup</b>\nConfiguring bot via <code>@BotFather</code>...")
            config = ctx.app.config.inline
            if config.bot_token and config.bot_username:
                config.is_enabled = True
                ctx.app.config_manager.set_inline_credentials(
                    username=config.bot_username,
                    token=config.bot_token,
                    placeholder="vibe_inline",
                    enabled=True,
                )
                created_username = config.bot_username
                created_token = config.bot_token
            else:
                try:
                    created = await ctx.app.botfather.create_inline_bot(placeholder="vibe_inline")
                except BotFatherRateLimitError as exc:
                    await ctx.edit(
                        "<b>⏳ Inline Setup Stopped</b>\n"
                        "BotFather returned a rate limit.\n"
                        f"<blockquote expandable>{exc}</blockquote>"
                    )
                    return
                ctx.app.config_manager.set_inline_credentials(
                    username=created.username,
                    token=created.token,
                    placeholder=created.placeholder,
                    enabled=True,
                )
                ctx.app.config.inline.bot_username = created.username
                ctx.app.config.inline.bot_token = created.token
                ctx.app.config.inline.placeholder = created.placeholder
                ctx.app.config.inline.is_enabled = True
                created_username = created.username
                created_token = created.token
            await ctx.app.inline.restart()
            delivery_note = await self._trigger_bot_start(ctx, created_username)
            await ctx.edit(
                "<b>✅ Inline Ready</b>\n"
                f"Bot: <code>{created_username}</code>\n"
                f"Placeholder: <code>vibe_inline</code>\n"
                f"{delivery_note}"
            )
            return

        if action == "restart":
            await ctx.app.inline.restart()
            await ctx.reply("<b>🔄 Inline</b>\nRestart completed.")
            return

        await ctx.reply(
            "<b>🤖 Inline Control</b>\n"
            "Usage:\n"
            "<code>inline setup</code>\n"
            "<code>inline status</code>\n"
            "<code>inline restart</code>"
        )

    async def _trigger_bot_start(self, ctx, username: str) -> str:
        try:
            await asyncio.sleep(2)
            await ctx.client.send_message(username, "/start")
            return "✉️ A <code>/start</code> message was sent to the bot. It should answer in its own chat."
        except Exception as exc:
            return (
                "⚠️ Bot is configured, but automatic <code>/start</code> delivery failed: "
                f"<code>{type(exc).__name__}: {exc}</code>"
            )


module = InlineModule()
