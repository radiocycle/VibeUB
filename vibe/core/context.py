from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, LinkPreviewOptions
from pyrogram.enums import ParseMode as PyrogramParseMode
from pyrogram.types import LinkPreviewOptions as PyrogramLinkPreviewOptions

if TYPE_CHECKING:
    from vibe.main import VibeUB


@dataclass(slots=True)
class CommandContext:
    app: "VibeUB"
    message: object
    command: str
    args: list[str]
    raw_args: str
    prefix: str
    started_at: float

    @property
    def client(self) -> object:
        return self.app.client

    @property
    def elapsed_ms(self) -> float:
        return (perf_counter() - self.started_at) * 1000

    async def reply(self, text: str, *, link_preview_options: PyrogramLinkPreviewOptions | None = None) -> object:
        editable = getattr(self.message, "edit_text", None)
        if editable is not None:
            try:
                return await editable(
                    text,
                    parse_mode=PyrogramParseMode.HTML,
                    link_preview_options=link_preview_options,
                )
            except Exception:
                pass
        return await self.message.reply_text(
            text,
            parse_mode=PyrogramParseMode.HTML,
            link_preview_options=link_preview_options,
        )

    async def edit(self, text: str, *, link_preview_options: PyrogramLinkPreviewOptions | None = None) -> object:
        return await self.message.edit_text(
            text,
            parse_mode=PyrogramParseMode.HTML,
            link_preview_options=link_preview_options,
        )

    async def react(self, emoji: str) -> None:
        send_reaction = getattr(self.message, "react", None)
        if send_reaction is not None:
            await send_reaction(emoji)

    async def send_photo(self, photo: str, caption: str, *, show_caption_above_media: bool = False) -> object:
        return await self.message.reply_photo(
            photo=photo,
            caption=caption,
            parse_mode=PyrogramParseMode.HTML,
            show_caption_above_media=show_caption_above_media,
        )

    async def edit_photo(self, photo: str, caption: str) -> object:
        from pyrogram.types import InputMediaPhoto

        return await self.message.edit_media(
            InputMediaPhoto(
                media=photo,
                caption=caption,
                parse_mode=PyrogramParseMode.HTML,
            )
        )

    async def delete(self) -> None:
        delete = getattr(self.message, "delete", None)
        if delete is not None:
            await delete()

@dataclass(slots=True)
class InlineQueryContext:
    app: "VibeUB"
    query: object

    def article(
        self,
        *,
        title: str,
        description: str,
        message_text: str,
        id_: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
        url: str | None = None,
        thumbnail_url: str | None = None,
        quote_media_url: str | None = None,
        invert_media: bool = False,
    ) -> InlineQueryResultArticle:
        return InlineQueryResultArticle(
            id=id_ or f"{title}:{abs(hash((title, description, message_text)))}",
            title=title,
            description=description,
            input_message_content=InputTextMessageContent(
                message_text=message_text,
                link_preview_options=LinkPreviewOptions(
                    is_disabled=not bool(quote_media_url),
                    url=quote_media_url,
                    show_above_text=bool(invert_media),
                    prefer_large_media=True if quote_media_url else None,
                ),
            ),
            reply_markup=reply_markup,
            url=url,
            thumbnail_url=thumbnail_url,
        )
