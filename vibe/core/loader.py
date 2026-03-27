from __future__ import annotations

import difflib
import importlib.util
import inspect
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from vibe.core.module import BaseModule, CommandSpec, InlineSpec

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RegisteredCommand:
    name: str
    aliases: tuple[str, ...]
    help_text: str
    callback: Any
    module_name: str
    module_title: str


@dataclass(slots=True)
class RegisteredInline:
    name: str
    description: str
    callback: Any
    module_name: str


class ModuleManager:
    def __init__(self, app: Any) -> None:
        self.app = app
        self._builtin_dir = (Path(__file__).resolve().parent.parent / "modules").resolve()
        self.modules: dict[str, BaseModule] = {}
        self.commands: dict[str, RegisteredCommand] = {}
        self.inline_handlers: dict[str, RegisteredInline] = {}
        self._loaded_python_modules: dict[str, ModuleType] = {}
        self._module_paths: dict[str, Path] = {}
        self._module_keys: dict[str, str] = {}

    async def load_all(self) -> None:
        custom_dir = self.app.config.resolved_modules_dir
        for directory in (self._builtin_dir, custom_dir):
            for path in sorted(directory.glob("*.py")):
                if path.name.startswith("_"):
                    continue
                await self.load_from_path(path)

    async def load_from_path(self, path: Path) -> BaseModule:
        module_key = f"vibe.dynamic.{path.stem}_{abs(hash(str(path.resolve())))}"
        spec = importlib.util.spec_from_file_location(module_key, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to create import spec for {path}")

        py_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(py_module)
        self._loaded_python_modules[module_key] = py_module

        module_obj = getattr(py_module, "module", None)
        if not isinstance(module_obj, BaseModule):
            raise RuntimeError(f"{path.name} must export `module = <BaseModule instance>`")

        if module_obj.name in self.modules:
            raise RuntimeError(f"Module `{module_obj.name}` is already loaded")

        module_obj.app = self.app
        self.modules[module_obj.name] = module_obj
        self._module_paths[module_obj.name] = path.resolve()
        self._module_keys[module_obj.name] = module_key
        self._register_module_members(module_obj)
        await module_obj.on_load()
        LOGGER.info("Loaded module %s from %s", module_obj.name, path)
        return module_obj

    async def unload(self, name: str) -> None:
        if name not in self.modules:
            raise KeyError(name)
        module = self.modules.pop(name)
        await module.on_unload()
        for command_name, command in list(self.commands.items()):
            if command.module_name == name:
                self.commands.pop(command_name, None)
        for handler_name, handler in list(self.inline_handlers.items()):
            if handler.module_name == name:
                self.inline_handlers.pop(handler_name, None)
        module_key = self._module_keys.pop(name, None)
        if module_key is not None:
            sys.modules.pop(module_key, None)
            self._loaded_python_modules.pop(module_key, None)
        self._module_paths.pop(name, None)

    async def reload(self, name: str) -> BaseModule:
        path = self.path_for(name)
        if path is None:
            raise KeyError(name)
        await self.unload(name)
        return await self.load_from_path(path)

    def path_for(self, name: str) -> Path | None:
        return self._module_paths.get(name)

    def delete_module_file(self, name: str) -> bool:
        path = self._module_paths.get(name)
        if path is None or self.is_core_module(name):
            return False
        if path.exists():
            path.unlink()
        return True

    def _register_module_members(self, module: BaseModule) -> None:
        for _, member in inspect.getmembers(module, predicate=callable):
            command_spec: CommandSpec | None = getattr(member, "__vibe_command__", None)
            if command_spec is not None:
                registered = RegisteredCommand(
                    name=command_spec.name,
                    aliases=command_spec.aliases,
                    help_text=command_spec.help_text,
                    callback=member,
                    module_name=module.name,
                    module_title=module.title,
                )
                self.commands[command_spec.name] = registered
                for alias in command_spec.aliases:
                    self.commands[alias] = registered

            inline_spec: InlineSpec | None = getattr(member, "__vibe_inline__", None)
            if inline_spec is not None:
                self.inline_handlers[inline_spec.name] = RegisteredInline(
                    name=inline_spec.name,
                    description=inline_spec.description,
                    callback=member,
                    module_name=module.name,
                )

    def list_primary_commands(self) -> list[RegisteredCommand]:
        unique: dict[tuple[str, str], RegisteredCommand] = {}
        for command in self.commands.values():
            unique[(command.module_name, command.name)] = command
        return sorted(unique.values(), key=lambda item: item.name)

    def get_module(self, query: str) -> BaseModule | None:
        lowered = query.lower()
        for module in self.modules.values():
            if (
                module.name.lower() == lowered
                or module.title.lower() == lowered
                or module.__class__.__name__.lower() == lowered
            ):
                return module
        return None

    def get_closest_module(self, query: str) -> BaseModule | None:
        direct = self.get_module(query)
        if direct is not None:
            return direct

        choices: dict[str, BaseModule] = {}
        for module in self.modules.values():
            choices[module.name.lower()] = module
            choices[module.title.lower()] = module
            choices[module.__class__.__name__.lower()] = module

        matches = difflib.get_close_matches(query.lower(), list(choices), n=1, cutoff=0.35)
        if not matches:
            return None
        return choices[matches[0]]

    def get_module_commands(self, module_name: str) -> list[RegisteredCommand]:
        unique: dict[str, RegisteredCommand] = {}
        for command in self.commands.values():
            if command.module_name == module_name:
                unique[command.name] = command
        return sorted(unique.values(), key=lambda item: item.name)

    def is_core_module(self, module_name: str) -> bool:
        path = self._module_paths.get(module_name)
        if path is None:
            return False
        try:
            path.relative_to(self._builtin_dir)
            return True
        except ValueError:
            return False
