from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class InlineConfig:
    bot_username: str | None = None
    bot_token: str | None = None
    placeholder: str = "vibe_inline"
    is_enabled: bool = False


@dataclass(slots=True)
class AppConfig:
    api_id: int = 0
    api_hash: str = ""
    session_name: str = "vibe"
    owner_id: int | None = None
    language: str = "en"
    prefix: str = "."
    workdir: str = "."
    modules_dir: str = "modules"
    config_path: str = "config.json"
    logs_dir: str = "logs"
    log_file: str = "vibe.log"
    log_level: str = "INFO"
    aliases: dict[str, str] = field(default_factory=dict)
    module_settings: dict[str, dict[str, Any]] = field(default_factory=dict)
    inline: InlineConfig = field(default_factory=InlineConfig)

    @property
    def resolved_workdir(self) -> Path:
        return Path(self.workdir).expanduser().resolve()

    @property
    def resolved_modules_dir(self) -> Path:
        return self.resolved_workdir / self.modules_dir

    @property
    def resolved_config_path(self) -> Path:
        return self.resolved_workdir / self.config_path

    @property
    def resolved_logs_dir(self) -> Path:
        return self.resolved_workdir / self.logs_dir

    @property
    def resolved_log_file(self) -> Path:
        return self.resolved_logs_dir / self.log_file


class ConfigManager:
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    @property
    def config(self) -> AppConfig:
        return self._config

    @classmethod
    def load(cls, *, workdir: str = ".", bot_token: str | None = None) -> "ConfigManager":
        workdir_path = Path(workdir).expanduser().resolve()
        config = AppConfig(
            api_id=_int_or_zero(os.getenv("VIBE_API_ID")),
            api_hash=os.getenv("VIBE_API_HASH", "").strip(),
            session_name=os.getenv("VIBE_SESSION_NAME", "vibe"),
            owner_id=_int_or_none(os.getenv("VIBE_OWNER_ID")),
            workdir=str(workdir_path),
            modules_dir=os.getenv("VIBE_MODULES_DIR", "modules"),
            config_path="config.json",
            logs_dir=os.getenv("VIBE_LOGS_DIR", "logs"),
            log_file=os.getenv("VIBE_LOG_FILE", "vibe.log"),
            log_level=os.getenv("VIBE_LOG_LEVEL", "INFO"),
        )
        manager = cls(config)
        manager.ensure_paths()
        manager._load_file()
        if bot_token:
            manager._config.inline.bot_token = bot_token
            manager._config.inline.is_enabled = True
        manager.save()
        return manager

    def ensure_paths(self) -> None:
        self._config.resolved_workdir.mkdir(parents=True, exist_ok=True)
        self._config.resolved_modules_dir.mkdir(parents=True, exist_ok=True)
        self._config.resolved_logs_dir.mkdir(parents=True, exist_ok=True)

    def _load_file(self) -> None:
        path = self._config.resolved_config_path
        if not path.exists():
            self.save()
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        self._config.api_id = int(payload.get("api_id", self._config.api_id or 0))
        self._config.api_hash = payload.get("api_hash", self._config.api_hash)
        self._config.session_name = payload.get("session_name", self._config.session_name)
        self._config.owner_id = payload.get("owner_id", self._config.owner_id)
        self._config.language = payload.get("language", self._config.language)
        self._config.prefix = payload.get("prefix", self._config.prefix)
        self._config.aliases = payload.get("aliases", {})
        self._config.module_settings = payload.get("module_settings", {})
        inline_payload = payload.get("inline", {})
        self._config.inline = InlineConfig(
            bot_username=inline_payload.get("bot_username"),
            bot_token=inline_payload.get("bot_token"),
            placeholder=inline_payload.get("placeholder", "vibe_inline"),
            is_enabled=inline_payload.get("is_enabled", False),
        )

    def save(self) -> None:
        path = self._config.resolved_config_path
        path.write_text(
            json.dumps(asdict(self._config), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def public_dict(self) -> dict[str, Any]:
        payload = asdict(self._config)
        token = payload["inline"].get("bot_token")
        if token:
            payload["inline"]["bot_token"] = f"{token[:8]}..."
        if payload.get("api_hash"):
            payload["api_hash"] = f"{payload['api_hash'][:8]}..."
        return payload

    def set_prefix(self, prefix: str) -> None:
        self._config.prefix = prefix
        self.save()

    def set_language(self, language: str) -> None:
        self._config.language = language
        self.save()

    def set_alias(self, alias: str, expansion: str) -> None:
        self._config.aliases[alias] = expansion
        self.save()

    def remove_alias(self, alias: str) -> bool:
        removed = self._config.aliases.pop(alias, None)
        if removed is not None:
            self.save()
            return True
        return False

    def set_api_credentials(self, *, api_id: int, api_hash: str) -> None:
        self._config.api_id = api_id
        self._config.api_hash = api_hash
        self.save()

    def set_inline_credentials(
        self,
        *,
        username: str,
        token: str,
        placeholder: str,
        enabled: bool = True,
    ) -> None:
        self._config.inline.bot_username = username
        self._config.inline.bot_token = token
        self._config.inline.placeholder = placeholder
        self._config.inline.is_enabled = enabled
        self.save()

    def get_module_option(self, module_name: str, key: str, default: Any = None) -> Any:
        return self._config.module_settings.get(module_name, {}).get(key, default)

    def set_module_option(self, module_name: str, key: str, value: Any) -> None:
        module_payload = self._config.module_settings.setdefault(module_name, {})
        module_payload[key] = value
        self.save()

    def reset_module_option(self, module_name: str, key: str) -> bool:
        module_payload = self._config.module_settings.get(module_name)
        if not module_payload or key not in module_payload:
            return False
        module_payload.pop(key, None)
        if not module_payload:
            self._config.module_settings.pop(module_name, None)
        self.save()
        return True


def _int_or_none(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    return int(value)


def _int_or_zero(value: str | None) -> int:
    if value is None or not value.strip():
        return 0
    return int(value)
