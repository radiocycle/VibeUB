from html import escape

from vibe.core import BaseModule, command


class HelpModule(BaseModule):
    name = "help"
    title = "Help"
    description = "List commands."

    @command("help", help_text="Show all modules or detailed help for one module.")
    async def help_command(self, ctx) -> None:
        if ctx.args:
            module = ctx.app.modules.get_closest_module(" ".join(ctx.args))
            if module is None:
                await ctx.reply("<b>📚 Help</b>\n❌ Module not found.")
                return
            commands = ctx.app.modules.get_module_commands(module.name)
            category = "core" if ctx.app.modules.is_core_module(module.name) else "external"
            lines = [
                f"<b>📦 {module.title}</b> <code>({module.name})</code>",
                f"Category: <code>{category}</code>",
                module.description,
            ]
            if commands:
                lines.append("<b>🛠 Commands</b>:")
                for item in commands:
                    alias_text = f" | aliases: {', '.join(item.aliases)}" if item.aliases else ""
                    lines.append(f"<code>{ctx.prefix}{item.name}</code> - {item.help_text or 'No description'}{alias_text}")
            else:
                lines.append("<b>🛠 Commands</b>: none")
            await ctx.reply("\n".join(lines))
            return

        core_lines: list[str] = []
        external_lines: list[str] = []

        for module in sorted(ctx.app.modules.modules.values(), key=lambda item: item.title.lower()):
            commands = ctx.app.modules.get_module_commands(module.name)
            command_names = ", ".join(f"{ctx.prefix}{item.name}" for item in commands) or "-"
            rendered = (
                f"&bull; <b>{escape(module.title)}</b> <code>({escape(module.name)})</code>: "
                f"<code>{escape(command_names)}</code>"
            )
            if ctx.app.modules.is_core_module(module.name):
                core_lines.append(rendered)
            else:
                external_lines.append(rendered)

        lines = [f"<b>📚 Vibe Help</b>\nPrefix: <code>{ctx.prefix}</code>"]
        lines.append("<b>🧩 Core</b>")
        lines.append(
            f"<blockquote expandable>{'\n'.join(core_lines) if core_lines else 'No core modules loaded.'}</blockquote>"
        )
        lines.append("<b>🧪 External</b>")
        lines.append(
            f"<blockquote expandable>{'\n'.join(external_lines) if external_lines else 'No external modules loaded.'}</blockquote>"
        )
        await ctx.reply("\n".join(lines))


module = HelpModule()
