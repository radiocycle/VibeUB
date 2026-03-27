from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from pyrogram.enums import ParseMode as PyrogramParseMode

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

    async def reply(self, text: str) -> object:
        editable = getattr(self.message, "edit_text", None)
        if editable is not None:
            try:
                return await editable(text, parse_mode=PyrogramParseMode.HTML)
            except Exception:
                pass
        return await self.message.reply_text(text, parse_mode=PyrogramParseMode.HTML)

    async def edit(self, text: str) -> object:
        return await self.message.edit_text(text, parse_mode=PyrogramParseMode.HTML)

    async def react(self, emoji: str) -> None:
        send_reaction = getattr(self.message, "react", None)
        if send_reaction is not None:
            await send_reaction(emoji)


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
    ) -> InlineQueryResultArticle:
        return InlineQueryResultArticle(
            id=id_ or f"{title}:{abs(hash((title, description, message_text)))}",
            title=title,
            description=description,
            input_message_content=InputTextMessageContent(message_text=message_text),
            reply_markup=reply_markup,
        )
