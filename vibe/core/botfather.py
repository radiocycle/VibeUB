from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from vibe.core.utils import extract_bot_token, random_bot_username

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CreatedInlineBot:
    username: str
    token: str
    placeholder: str


class BotFatherRateLimitError(RuntimeError):
    pass


class BotFatherService:
    def __init__(self, client: object) -> None:
        self.client = client
        self.chat_id = "BotFather"

    async def create_inline_bot(
        self,
        *,
        display_name: str = "VibeUB Inline",
        username_prefix: str = "vibe",
        placeholder: str = "vibe_inline",
        timeout: int = 90,
    ) -> CreatedInlineBot:
        cancel_message = await self._send("/cancel")
        await self._wait_reply(after=cancel_message.id, timeout=8)
        newbot_message = await self._send("/newbot")
        prompt = await self._wait_reply(after=newbot_message.id, timeout=timeout)
        if "choose a name" not in prompt.text.lower():
            LOGGER.warning("Unexpected BotFather reply after /newbot: %s", prompt.text)
        name_message = await self._send(display_name)
        username_prompt = await self._wait_reply(after=name_message.id, timeout=timeout)

        token: str | None = None
        accepted_username: str | None = None
        last_reply_id = username_prompt.id
        for _ in range(12):
            username = random_bot_username(username_prefix)
            username_message = await self._send(username)
            reply = await self._wait_reply(after=max(last_reply_id, username_message.id), timeout=timeout)
            last_reply_id = reply.id
            if "sorry" in reply.text.lower() or "already taken" in reply.text.lower():
                continue
            token = extract_bot_token(reply.text)
            if token:
                accepted_username = username
                break
        if token is None or accepted_username is None:
            raise RuntimeError("Failed to allocate a free bot username via BotFather.")

        await self._configure_inline(accepted_username, placeholder, timeout=timeout)
        return CreatedInlineBot(
            username=f"@{accepted_username}",
            token=token,
            placeholder=placeholder,
        )

    async def _configure_inline(self, username: str, placeholder: str, *, timeout: int) -> None:
        command_message = await self._send("/setinline")
        first = await self._wait_reply(after=command_message.id, timeout=timeout)
        bot_message = await self._send(f"@{username}")
        second = await self._wait_reply(after=max(first.id, bot_message.id), timeout=timeout)
        if "placeholder" not in second.text.lower():
            LOGGER.warning("Unexpected reply after /setinline selection: %s", second.text)
        placeholder_message = await self._send(placeholder)
        await self._wait_reply(after=max(second.id, placeholder_message.id), timeout=timeout)

    async def _send(self, text: str) -> object:
        return await self.client.send_message(self.chat_id, text)

    async def _wait_reply(self, *, after: int = 0, timeout: int = 60) -> object:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            async for message in self.client.get_chat_history(self.chat_id, limit=6):
                if getattr(message, "id", 0) <= after:
                    break
                if getattr(message, "from_user", None) and getattr(message.from_user, "is_bot", False):
                    text = getattr(message, "text", None) or getattr(message, "caption", "")
                    if text:
                        lowered = text.lower()
                        if "sorry, too many attempts" in lowered:
                            raise BotFatherRateLimitError(text)
                        return _Reply(id=message.id, text=text)
            await asyncio.sleep(1.5)
        raise TimeoutError("Timed out waiting for BotFather reply.")


@dataclass(slots=True)
class _Reply:
    id: int
    text: str
