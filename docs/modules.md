# Writing modules for Vibe

Vibe modules are plain Python files loaded from either:

- `vibe/modules/`
- `./modules/`

## Minimal module

```python
from vibe.core import BaseModule, ModuleOption, command, inline_handler


class EchoModule(BaseModule):
    name = "echo"
    title = "Echo"
    description = "Simple echo module."

    @command("echo", help_text="Repeat text back.")
    async def echo(self, ctx):
        if not ctx.args:
            await ctx.reply("Usage: echo <text>")
            return
        await ctx.reply(ctx.raw_args)

    @inline_handler("echo", description="Return provided text")
    async def echo_inline(self, query):
        text = query.query.partition(" ")[2] or "empty"
        return [query.article(
            title="Echo",
            description=text,
            message_text=text,
        )]


module = EchoModule()
```

## Rules

- Export a module instance named `module`.
- Inherit from `BaseModule`.
- Define both `name` and `title`.
- Register commands with `@command(...)`.
- Register inline handlers with `@inline_handler(...)`.
- Keep external state inside `self.storage` or in the main config.

## Command context

Every command receives `CommandContext` as `ctx`.

Useful fields:

- `ctx.message`: original Telegram message.
- `ctx.args`: split arguments list.
- `ctx.raw_args`: raw string after command name.
- `ctx.command`: command name.
- `ctx.prefix`: current command prefix.
- `ctx.app`: current `VibeUB` application.
- `ctx.client`: `pyrogram`-compatible client from the `kurigram` package.

Useful methods:

- `await ctx.reply(text)`
- `await ctx.edit(text)`
- `await ctx.react("⚡")`

## Dynamic module loading

- `.loadmod` with a replied Python file downloads the file into the custom modules directory and loads it.
- `.downloadmod <url>` fetches a Python module from a URL, stores it, then loads it.
- `.unloadmod <name>` unloads a loaded module.
- `.reloadmod <name>` unloads and imports the module again from disk.

## Module options for config panel

Expose module options through `get_options()`:

```python
def get_options(self) -> list[ModuleOption]:
    return [
        ModuleOption(
            key="enabled",
            label="Enabled",
            description="Whether the module should run",
            value="yes",
        )
    ]
```

These options are shown in the inline `config` panel as buttons.

## Recommendations

- Pick a unique module `name`.
- Keep command names short and predictable.
- Handle invalid arguments explicitly.
- Avoid blocking I/O. Use async APIs.
- If your module depends on third-party libraries, document that dependency clearly.
