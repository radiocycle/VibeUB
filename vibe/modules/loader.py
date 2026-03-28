from html import escape

from vibe.core import BaseModule, command
from vibe.core.utils import download_text, safe_filename_from_url


class LoaderModule(BaseModule):
    name = "loader"
    title = "Loader"
    description = "Dynamic module loader."

    @command("loadmod", help_text="Load a module from a replied .py file.")
    async def loadmod(self, ctx) -> None:
        replied = getattr(ctx.message, "reply_to_message", None)
        if replied is None or getattr(replied, "document", None) is None:
            await ctx.reply("<b>📦 Loader</b>\nReply to a Python file with this command.")
            return

        file_name = replied.document.file_name or "module.py"
        if not file_name.endswith(".py"):
            await ctx.reply("<b>📦 Loader</b>\nOnly <code>.py</code> files can be loaded as modules.")
            return

        target = ctx.app.config.resolved_modules_dir / file_name
        await replied.download(file_name=str(target))
        module = await ctx.app.modules.load_from_path(target)
        await ctx.reply(self._module_loaded_text(ctx, module.name, file_name))

    @command("downloadmod", help_text="Download and load a module from URL.")
    async def downloadmod(self, ctx) -> None:
        if not ctx.args:
            await ctx.reply("<b>📦 Loader</b>\nUsage: <code>downloadmod &lt;url&gt;</code>")
            return
        url = ctx.args[0]
        content = await download_text(url)
        filename = safe_filename_from_url(url)
        target = ctx.app.config.resolved_modules_dir / filename
        target.write_text(content, encoding="utf-8")
        module = await ctx.app.modules.load_from_path(target)
        await ctx.reply(self._module_loaded_text(ctx, module.name, url, heading="Module Downloaded", label="Source"))

    @command("modules", help_text="List loaded modules.")
    async def modules_command(self, ctx) -> None:
        names = ", ".join(sorted(ctx.app.modules.modules))
        await ctx.reply(f"<b>🧩 Loaded Modules</b>\n<code>{names}</code>")

    @command("unloadmod", help_text="Unload a module by name.")
    async def unloadmod(self, ctx) -> None:
        if not ctx.args:
            await ctx.reply("<b>📦 Loader</b>\nUsage: <code>unloadmod &lt;module&gt;</code>")
            return
        module = ctx.app.modules.get_closest_module(ctx.args[0])
        if module is None:
            await ctx.reply(f"<b>📦 Loader</b>\nModule <code>{escape(ctx.args[0])}</code> is not loaded.")
            return
        name = module.name
        if name in {"loader", "help", "system"}:
            await ctx.reply("<b>📦 Loader</b>\nThis module is protected from unload.")
            return
        removed_from_disk = ctx.app.modules.delete_module_file(name)
        try:
            await ctx.app.modules.unload(name)
        except KeyError:
            await ctx.reply(f"<b>📦 Loader</b>\nModule <code>{name}</code> is not loaded.")
            return
        if removed_from_disk:
            await ctx.reply(
                "<b>🗑 Module Unloaded</b>\n"
                f"Name: <code>{name}</code>\n"
                "State: <code>removed from disk</code>"
            )
            return
        await ctx.reply(
            "<b>🧠 Module Unloaded</b>\n"
            f"Name: <code>{name}</code>\n"
            "State: <code>unloaded from memory only</code>"
        )

    @command("reloadmod", help_text="Reload a module by name.")
    async def reloadmod(self, ctx) -> None:
        if not ctx.args:
            await ctx.reply("<b>📦 Loader</b>\nUsage: <code>reloadmod &lt;module&gt;</code>")
            return
        name = ctx.args[0]
        try:
            module = await ctx.app.modules.reload(name)
        except KeyError:
            await ctx.reply(f"<b>📦 Loader</b>\nModule <code>{name}</code> is not loaded.")
            return
        await ctx.reply(self._module_loaded_text(ctx, module.name, name, heading="Module Reloaded", label="Target"))

    @command("addalias", help_text="Add a command alias: addalias p ping")
    async def addalias(self, ctx) -> None:
        if len(ctx.args) < 2:
            await ctx.reply("<b>🔗 Aliases</b>\nUsage: <code>addalias &lt;alias&gt; &lt;command...&gt;</code>")
            return
        alias = ctx.args[0].lower()
        expansion = " ".join(ctx.args[1:]).strip()
        command_name = ctx.args[1].lower()
        command = ctx.app.modules.commands.get(command_name)
        if command is None:
            await ctx.reply(f"<b>🔗 Aliases</b>\nCommand <code>{escape(command_name)}</code> was not found.")
            return
        if alias == command.name:
            await ctx.reply("<b>🔗 Aliases</b>\nAlias must be different from the original command name.")
            return
        ctx.app.config_manager.set_alias(alias, expansion)
        ctx.app.config.aliases[alias] = expansion
        await ctx.reply(
            "<b>✅ Alias Added</b>\n"
            f"Alias: <code>{escape(alias)}</code>\n"
            f"Expansion: <code>{escape(expansion)}</code>"
        )

    @command("remalias", help_text="Remove an alias: remalias p")
    async def remalias(self, ctx) -> None:
        if len(ctx.args) != 1:
            await ctx.reply("<b>🔗 Aliases</b>\nUsage: <code>remalias &lt;alias&gt;</code>")
            return
        alias = ctx.args[0].lower()
        if not ctx.app.config_manager.remove_alias(alias):
            await ctx.reply(f"<b>🔗 Aliases</b>\nAlias <code>{escape(alias)}</code> was not found.")
            return
        ctx.app.config.aliases.pop(alias, None)
        await ctx.reply(f"<b>🗑 Alias Removed</b>\nAlias: <code>{escape(alias)}</code>")

    @command("aliases", help_text="List configured aliases.")
    async def aliases(self, ctx) -> None:
        aliases = ctx.app.config.aliases
        if not aliases:
            await ctx.reply("<b>🔗 Aliases</b>\nNo aliases configured.")
            return
        lines = [f"&bull; <code>{escape(alias)}</code> -&gt; <code>{escape(command)}</code>" for alias, command in sorted(aliases.items())]
        await ctx.reply(
            "<b>🔗 Aliases</b>\n"
            f"<blockquote expandable>{''.join(line + chr(10) for line in lines).rstrip()}</blockquote>"
        )

    def _module_loaded_text(
        self,
        ctx,
        module_name: str,
        source: str,
        *,
        heading: str = "Module Loaded",
        label: str = "File",
    ) -> str:
        commands = ctx.app.modules.get_module_commands(module_name)
        if commands:
            command_lines = [
                f"&bull; <code>{escape(ctx.prefix + item.name)}</code> - {escape(item.help_text or 'No description')}"
                for item in commands
            ]
            commands_block = f"<blockquote expandable>{''.join(line + chr(10) for line in command_lines).rstrip()}</blockquote>"
        else:
            commands_block = "<blockquote expandable>No commands exported.</blockquote>"
        return (
            f"<b>📦 {heading}</b>\n"
            f"Name: <code>{escape(module_name)}</code>\n"
            f"{label}: <code>{escape(source)}</code>\n"
            "<b>🛠 Commands</b>\n"
            f"{commands_block}"
        )


module = LoaderModule()
