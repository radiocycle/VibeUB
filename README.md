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

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/radiocycle/VibeUB.git
cd VibeUB
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Optional but recommended for faster Telegram crypto:

```bash
pip install tgcrypto
```

### 4. Start VibeUB

```bash
python -m vibe
```

On first launch VibeUB asks for:

- `api_id`
- `api_hash`

Get them from:

```text
https://my.telegram.org
```

After that:

- `config.json` is created locally
- `vibe.session` appears after successful login
- your Telegram account session is stored on disk

### 5. Log in to Telegram

When Pyrogram starts, enter:

- your phone number
- the login code from Telegram
- password if 2FA is enabled

### 6. Configure inline mode

Inside your Telegram saved messages or any chat where you use the userbot:

```text
.inline setup
```

This will:

- create a bot through `@BotFather` if needed
- enable inline mode
- set inline placeholder to `vibe_inline`
- save the bot token locally

### 7. Basic commands

```text
.help
.info
.ping
.config
.inline status
```

### Updating

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt
```

If needed, restart the bot:

```text
.restart
```

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

## Troubleshooting

### `The api_id/api_hash combination is invalid`

Your Telegram API credentials are wrong.

Fix:

- open `https://my.telegram.org`
- generate or copy your real `api_id` and `api_hash`
- delete or edit local `config.json`
- start VibeUB again and enter the correct values

### `ModuleNotFoundError: No module named 'kurigram'`

The `kurigram` package exposes a `pyrogram`-compatible runtime. VibeUB already imports the correct runtime internally.

Fix:

- activate the virtual environment
- reinstall dependencies:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### `TgCrypto is missing`

This is not fatal. The bot will still work, but Telegram encryption will be slower.

Fix:

```bash
pip install tgcrypto
```

### Bot creation fails with `Sorry, too many attempts`

`@BotFather` rate-limited the account.

Fix:

- wait until the timeout from the BotFather message expires
- run `.inline setup` again later

VibeUB stops the creation process automatically when this message appears.

### `Ctrl+C` does not stop the process cleanly

If shutdown hangs, update to the latest version of the repository. Recent fixes disable signal interception inside the inline polling layer and route shutdown through the main app.

Recommended steps:

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt
python -m vibe
```

### Inline bot is configured but does not answer

Check:

- `.inline status`
- whether the saved bot token is valid
- whether the bot was started with `/start`
- whether inline mode was enabled in `@BotFather`

If needed:

```text
.inline restart
```

### External module comes back after restart

Use `.unloadmod <module>` on the latest version.

Current behavior:

- external module file is deleted from `./modules/`
- module is removed from memory
- it should not be loaded again after restart

### `logs` / media editing fails

Telegram may reject converting a particular message into a file/media message depending on message type and chat context.

If this happens:

- run the command from a normal text command message
- avoid using very old or special-service messages as the source

### Session problems or broken `vibe.session`

If the session file is corrupted or was manually edited, login can fail.

Fix:

```bash
rm -f vibe.session
python -m vibe
```

You will need to log in again.

## Notes

- Local files like `config.json`, `vibe.session`, logs and user-installed modules are intentionally not meant for publishing.
- `eval` and `terminal` are trusted owner-only style commands and should be treated accordingly.
