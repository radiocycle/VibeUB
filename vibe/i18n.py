from __future__ import annotations

from vibe.langpacks import DEFAULT_LANGUAGE, LANGPACKS


class Localizer:
    def __init__(self, app) -> None:
        self.app = app

    @property
    def language(self) -> str:
        return self.app.config.language if self.app.config.language in LANGPACKS else DEFAULT_LANGUAGE

    def text(self, key: str, **kwargs) -> str:
        pack = LANGPACKS.get(self.language, LANGPACKS[DEFAULT_LANGUAGE])
        template = pack.get(key) or LANGPACKS[DEFAULT_LANGUAGE].get(key) or key
        return template.format(**kwargs)
