from time import perf_counter

from pyrogram.types import LinkPreviewOptions

from vibe import __version__
from vibe.core import BaseModule, ModuleOption, command, inline_handler


DEFAULT_INFO_TEMPLATE = (
    "<b>ℹ️ Vibe Information</b>\n"
    "👤 User: <code>@{username}</code>\n"
    "🪪 Name: <code>{first_name}</code>\n"
    "🆔 User ID: <code>{user_id}</code>\n"
    "🧬 Version: <code>{version}</code>\n"
    "🧩 Modules: <code>{modules_count}</code>\n"
    "🤖 Inline bot: <code>{inline_bot}</code>\n"
    "⏱ Uptime: <code>{uptime}</code>"
)

DEFAULT_INLINE_INFO_TEMPLATE = (
    "<b>ℹ️ Vibe Information</b>\n"
    "👤 User: <code>@{username}</code>\n"
    "🧩 Modules: <code>{modules_count}</code>"
)

DEFAULT_INLINE_INFO_BANNER_URL = ""
DEFAULT_INLINE_INFO_QUOTE_MEDIA = True
DEFAULT_INLINE_INFO_INVERT_MEDIA = False

INFO_PLACEHOLDERS = (
    ("{username}", "account username"),
    ("{first_name}", "account first name"),
    ("{user_id}", "Telegram user id"),
    ("{version}", "userbot version"),
    ("{modules_count}", "loaded modules count"),
    ("{inline_bot}", "inline bot username"),
    ("{uptime}", "human readable uptime"),
)


class _SafeFormat(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _bool_value(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enable", "enabled"}


class InfoModule(BaseModule):
    name = "info"
    title = "Info"
    description = "Show userbot info."

    @command("info", help_text="Show current account, uptime and loaded modules.")
    async def info(self, ctx) -> None:
        me = ctx.app.me
        uptime = perf_counter() - ctx.app.started_at
        inline_username = ctx.app.config.inline.bot_username or "not configured"
        template = ctx.app.config_manager.get_module_option(
            self.name,
            "custom_text",
            ctx.app.config_manager.get_module_option(self.name, "template", DEFAULT_INFO_TEMPLATE),
        )
        try:
            rendered = template.format_map(self._placeholders(ctx.app, me, uptime, inline_username))
        except Exception as exc:
            await ctx.reply(f"<b>❌ Info Template Error</b>\n<code>{type(exc).__name__}: {exc}</code>")
            return
        banner_url = ctx.app.config_manager.get_module_option(self.name, "banner_url", DEFAULT_INLINE_INFO_BANNER_URL) or None
        quote_media = _bool_value(
            ctx.app.config_manager.get_module_option(
                self.name,
                "quote_media",
                DEFAULT_INLINE_INFO_QUOTE_MEDIA,
            )
        )
        invert_media = _bool_value(
            ctx.app.config_manager.get_module_option(self.name, "invert_media", DEFAULT_INLINE_INFO_INVERT_MEDIA)
        )
        if banner_url and not quote_media:
            if not invert_media:
                try:
                    await ctx.edit_photo(banner_url, rendered)
                    return
                except Exception:
                    pass
            await ctx.send_photo(banner_url, rendered, show_caption_above_media=invert_media)
            await ctx.delete()
            return
        await ctx.reply(
            rendered,
            link_preview_options=self._build_preview_options(banner_url, quote_media, invert_media),
        )

    @inline_handler("info", description="Send VibeUB info")
    async def inline_info(self, query):
        me = query.app.me
        template = query.app.config_manager.get_module_option(
            self.name,
            "custom_text",
            query.app.config_manager.get_module_option(self.name, "inline_template", DEFAULT_INLINE_INFO_TEMPLATE),
        )
        uptime = perf_counter() - query.app.started_at
        inline_username = query.app.config.inline.bot_username or "not configured"
        placeholders = self._placeholders(query.app, me, uptime, inline_username)
        try:
            rendered = template.format_map(placeholders)
        except Exception:
            rendered = DEFAULT_INLINE_INFO_TEMPLATE.format_map(placeholders)
        banner_url = query.app.config_manager.get_module_option(self.name, "banner_url", DEFAULT_INLINE_INFO_BANNER_URL) or None
        quote_media = _bool_value(
            query.app.config_manager.get_module_option(
                self.name,
                "quote_media",
                DEFAULT_INLINE_INFO_QUOTE_MEDIA,
            )
        )
        invert_media = _bool_value(
            query.app.config_manager.get_module_option(self.name, "invert_media", DEFAULT_INLINE_INFO_INVERT_MEDIA)
        )
        return [
            query.article(
                title="ℹ️ Vibe Information",
                description=f"👤 @{getattr(me, 'username', 'unknown')} • 🧩 {len(query.app.modules.modules)} modules",
                message_text=rendered,
                thumbnail_url=banner_url,
                quote_media_url=banner_url if quote_media else None,
                invert_media=invert_media,
            )
        ]

    def get_options(self) -> list[ModuleOption]:
        return [
            ModuleOption(
                key="custom_text",
                label="Custom Text",
                description="HTML template for info and inline info.",
                value=self.app.config_manager.get_module_option(
                    self.name,
                    "custom_text",
                    self.app.config_manager.get_module_option(self.name, "template", DEFAULT_INFO_TEMPLATE),
                )[:48] + "...",
                editable=True,
                placeholders=INFO_PLACEHOLDERS,
                value_type="string",
            ),
            ModuleOption(
                key="banner_url",
                label="Banner URL",
                description="URL used as webpage preview source for commands and thumbnail for inline results.",
                value=self.app.config_manager.get_module_option(self.name, "banner_url", DEFAULT_INLINE_INFO_BANNER_URL) or "not set",
                editable=True,
                value_type="string",
            ),
            ModuleOption(
                key="quote_media",
                label="Quote Media",
                description="When enabled, use banner_url as webpage preview. When disabled, send banner_url as photo banner.",
                value=str(
                    self.app.config_manager.get_module_option(
                        self.name,
                        "quote_media",
                        DEFAULT_INLINE_INFO_QUOTE_MEDIA,
                    )
                ).lower(),
                editable=True,
                value_type="boolean",
            ),
            ModuleOption(
                key="invert_media",
                label="Invert Media",
                description="Show webpage preview above the text where Telegram supports it. Values: true/false.",
                value=str(
                    self.app.config_manager.get_module_option(
                        self.name,
                        "invert_media",
                        DEFAULT_INLINE_INFO_INVERT_MEDIA,
                    )
                ).lower(),
                editable=True,
                value_type="boolean",
            ),
        ]

    def _placeholders(self, app, me, uptime: float, inline_username: str) -> _SafeFormat:
        return _SafeFormat(
            username=getattr(me, "username", "unknown"),
            first_name=getattr(me, "first_name", "unknown"),
            user_id=getattr(me, "id", "unknown"),
            version=__version__,
            modules_count=len(app.modules.modules),
            inline_bot=inline_username,
            uptime=self._format_uptime(int(uptime)),
        )

    def _format_uptime(self, seconds: int) -> str:
        parts: list[str] = []
        units = (
            ("day(s)", 86400),
            ("hour(s)", 3600),
            ("min(s)", 60),
            ("sec(s)", 1),
        )
        remaining = max(seconds, 0)
        for label, size in units:
            if size == 1:
                parts.append(f"{remaining} {label}")
                break
            value, remaining = divmod(remaining, size)
            if value:
                parts.append(f"{value} {label}")
        return ", ".join(parts) if parts else "0 sec(s)"

    def _build_preview_options(
        self,
        banner_url: str | None,
        quote_media: bool,
        invert_media: bool,
    ) -> LinkPreviewOptions:
        if not banner_url or not quote_media:
            return LinkPreviewOptions(is_disabled=True)
        return LinkPreviewOptions(
            is_disabled=False,
            url=banner_url,
            show_above_text=invert_media,
            prefer_large_media=True,
        )

module = InfoModule()
