from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


CommandCallable = Callable[..., Awaitable[Any]]
InlineCallable = Callable[..., Awaitable[Any]]


@dataclass(slots=True)
class CommandSpec:
    name: str
    help_text: str
    aliases: tuple[str, ...]


@dataclass(slots=True)
class InlineSpec:
    name: str
    description: str


@dataclass(slots=True)
class ModuleOption:
    key: str
    label: str
    description: str
    value: Any = ""
    editable: bool = False
    placeholders: tuple[tuple[str, str], ...] = ()
    value_type: str = "string"
    choices: tuple[str, ...] = ()


def command(name: str, *, help_text: str = "", aliases: tuple[str, ...] = ()) -> Callable[[CommandCallable], CommandCallable]:
    def decorator(func: CommandCallable) -> CommandCallable:
        setattr(func, "__vibe_command__", CommandSpec(name=name, help_text=help_text, aliases=aliases))
        return func
    return decorator


def inline_handler(name: str, *, description: str = "") -> Callable[[InlineCallable], InlineCallable]:
    def decorator(func: InlineCallable) -> InlineCallable:
        setattr(func, "__vibe_inline__", InlineSpec(name=name, description=description))
        return func
    return decorator


class BaseModule:
    name = "base"
    title = "Base"
    description = "Base module"

    def __init__(self) -> None:
        self.app = None
        self.storage: dict[str, Any] = {}

    async def on_load(self) -> None:
        return None

    async def on_unload(self) -> None:
        return None

    def get_options(self) -> list[ModuleOption]:
        return []
