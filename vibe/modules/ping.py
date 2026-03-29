from time import perf_counter_ns

from pyrogram.types import LinkPreviewOptions

from vibe.core import BaseModule, ModuleOption, command, inline_handler


DEFAULT_PING_TESTING_TEMPLATE = "<b>📡 Testing latency...</b>"
DEFAULT_PING_RESULT_TEMPLATE = (
    "<b>🏓 Pong</b>\n"
    "Edit latency: <code>{latency_ms:.2f} ms</code>"
)
DEFAULT_INLINE_PING_TEMPLATE = "<b>🏓 Ping</b>\n📡 Runtime latency check is ready."
DEFAULT_INLINE_PING_BANNER_URL = ""
DEFAULT_INLINE_PING_QUOTE_MEDIA = True
DEFAULT_INLINE_PING_INVERT_MEDIA = False

PING_PLACEHOLDERS = (
    ("{latency_ms}", "measured edit latency in milliseconds"),
)


class _SafeFormat(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _bool_value(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enable", "enabled"}


class PingModule(BaseModule):
    name = "ping"
    title = "Ping"
    description = "Latency test."

    @command("ping", help_text="Measure command processing latency.")
    async def ping(self, ctx) -> None:
        testing_template = ctx.app.config_manager.get_module_option(
            self.name,
            "testing_template",
            DEFAULT_PING_TESTING_TEMPLATE,
        )
        result_template = ctx.app.config_manager.get_module_option(
            self.name,
            "result_template",
            DEFAULT_PING_RESULT_TEMPLATE,
        )
        started = perf_counter_ns()
        await ctx.edit(testing_template)
        latency_ms = (perf_counter_ns() - started) / 1_000_000
        try:
            rendered = result_template.format_map(_SafeFormat(latency_ms=latency_ms))
        except Exception as exc:
            await ctx.edit(f"<b>❌ Ping Template Error</b>\n<code>{type(exc).__name__}: {exc}</code>")
            return
        banner_url = ctx.app.config_manager.get_module_option(self.name, "banner_url", DEFAULT_INLINE_PING_BANNER_URL) or None
        quote_media = _bool_value(
            ctx.app.config_manager.get_module_option(
                self.name,
                "quote_media",
                DEFAULT_INLINE_PING_QUOTE_MEDIA,
            )
        )
        invert_media = _bool_value(
            ctx.app.config_manager.get_module_option(
                self.name,
                "invert_media",
                DEFAULT_INLINE_PING_INVERT_MEDIA,
            )
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
        await ctx.edit(
            rendered,
            link_preview_options=self._build_preview_options(banner_url, quote_media, invert_media),
        )

    @inline_handler("ping", description="Send ping card")
    async def inline_ping(self, query):
        template = query.app.config_manager.get_module_option(
            self.name,
            "custom_text",
            query.app.config_manager.get_module_option(
                self.name,
                "inline_template",
                DEFAULT_INLINE_PING_TEMPLATE,
            ),
        )
        banner_url = query.app.config_manager.get_module_option(
            self.name,
            "banner_url",
            DEFAULT_INLINE_PING_BANNER_URL,
        ) or None
        quote_media = _bool_value(
            query.app.config_manager.get_module_option(
                self.name,
                "quote_media",
                DEFAULT_INLINE_PING_QUOTE_MEDIA,
            )
        )
        invert_media = _bool_value(
            query.app.config_manager.get_module_option(
                self.name,
                "invert_media",
                DEFAULT_INLINE_PING_INVERT_MEDIA,
            )
        )
        placeholders = _SafeFormat(latency_ms="0.00")
        try:
            rendered = template.format_map(placeholders)
        except Exception:
            rendered = DEFAULT_INLINE_PING_TEMPLATE
        return [
            query.article(
                title="🏓 Ping",
                description="📡 Send a latency check card",
                message_text=rendered,
                thumbnail_url=banner_url,
                quote_media_url=banner_url if quote_media else None,
                invert_media=invert_media,
            )
        ]

    def get_options(self) -> list[ModuleOption]:
        return [
            ModuleOption(
                key="testing_template",
                label="Testing Text",
                description="HTML text shown before latency result.",
                value=self.app.config_manager.get_module_option(self.name, "testing_template", DEFAULT_PING_TESTING_TEMPLATE),
                default=DEFAULT_PING_TESTING_TEMPLATE,
                editable=True,
                placeholders=PING_PLACEHOLDERS,
            ),
            ModuleOption(
                key="result_template",
                label="Result Text",
                description="HTML text.",
                value=self.app.config_manager.get_module_option(self.name, "result_template", DEFAULT_PING_RESULT_TEMPLATE)[:48] + "...",
                default=DEFAULT_PING_RESULT_TEMPLATE,
                editable=True,
                placeholders=PING_PLACEHOLDERS,
            ),
            ModuleOption(
                key="custom_text",
                label="Custom Text",
                description="HTML text for inline ping result.",
                value=self.app.config_manager.get_module_option(
                    self.name,
                    "custom_text",
                    self.app.config_manager.get_module_option(
                        self.name,
                        "inline_template",
                        DEFAULT_INLINE_PING_TEMPLATE,
                    ),
                )[:48] + "...",
                default=DEFAULT_INLINE_PING_TEMPLATE,
                editable=True,
                placeholders=PING_PLACEHOLDERS,
                value_type="string",
            ),
            ModuleOption(
                key="banner_url",
                label="Banner URL",
                description="URL used as webpage preview source for commands and thumbnail for inline results.",
                value=self.app.config_manager.get_module_option(self.name, "banner_url", DEFAULT_INLINE_PING_BANNER_URL) or "not set",
                default=DEFAULT_INLINE_PING_BANNER_URL,
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
                        DEFAULT_INLINE_PING_QUOTE_MEDIA,
                    )
                ).lower(),
                default=DEFAULT_INLINE_PING_QUOTE_MEDIA,
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
                        DEFAULT_INLINE_PING_INVERT_MEDIA,
                    )
                ).lower(),
                default=DEFAULT_INLINE_PING_INVERT_MEDIA,
                editable=True,
                value_type="boolean",
            ),
        ]

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

module = PingModule()
