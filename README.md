# VibeUB

VibeUB is a modular Telegram userbot built on the `kurigram` package with a `pyrogram`-compatible runtime, plus an inline-bot layer powered by `aiogram`.

> Vibecoded userbot.

## Highlights

- Modular architecture with load, reload and unload support.
- Core commands for help, config, ping, info, logs, restart, aliases and module management.
- Inline bot setup through `@BotFather`, including automatic username generation and inline mode configuration.
- Inline config panel with buttons for module options.
- Pretty formatted responses, expandable help blocks and module command previews after loading.
- Documentation for writing third-party modules.

## Features

- Built-in commands: `help`, `ping`, `info`, `config`, `loadmod`, `downloadmod`, `unloadmod`, `reloadmod`, `addalias`, `remalias`, `aliases`, `logs`, `restart`, `eval`, `terminal`, `setprefix`, `inline`.
- Support for external modules stored separately from the core.
- Safe interactive bootstrap for `api_id` and `api_hash`.
- Optional inline bot token override through CLI.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m vibe
```

On first launch VibeUB asks for Telegram API credentials and stores them locally.

## Launch Options

```bash
python -m vibe --bot-token "<token>"
python -m vibe --root
```

- `--bot-token "<token>"` uses an already created bot token for inline mode.
- `--root` explicitly allows running as root. Without it, startup is blocked.

## Project Layout

```text
VibeUB/
├── README.md
├── docs/
│   └── modules.md
├── pyproject.toml
├── requirements.txt
└── vibe/
    ├── core/
    ├── modules/
    ├── bootstrap.py
    ├── __main__.py
    ├── config.py
    ├── logging.py
    └── main.py
```

## Inline

Use Telegram commands from your account:

- `.inline setup` creates and configures an inline bot through `@BotFather`
- `.inline status` shows current inline state
- `.inline restart` restarts inline polling
- `.config` opens the inline config panel

If Telegram changes `@BotFather` texts, the automation flow may need small adjustments.

## Modules

VibeUB supports both:

- `core` modules bundled with the project
- `external` modules loaded from user files or URLs

Module authoring docs live in [docs/modules.md](/home/kat/Code/vibe-ub/docs/modules.md).

## Notes

- Local files like `config.json`, `vibe.session`, logs and user-installed modules are intentionally not meant for publishing.
- `eval` and `terminal` are trusted owner-only style commands and should be treated accordingly.
