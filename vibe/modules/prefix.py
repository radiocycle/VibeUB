from vibe.core import BaseModule, ModuleOption, command


class PrefixModule(BaseModule):
    name = "prefix"
    title = "Prefix"
    description = "Change prefix."

    @command("setprefix", help_text="Change command prefix: setprefix !")
    async def setprefix(self, ctx) -> None:
        if not ctx.args or len(ctx.args[0]) > 3:
            await ctx.reply("<b>🔣 Prefix</b>\nUsage: <code>setprefix &lt;prefix&gt;</code>")
            return
        new_prefix = ctx.args[0]
        ctx.app.config_manager.set_prefix(new_prefix)
        ctx.app.config.prefix = new_prefix
        await ctx.reply(f"<b>✅ Prefix Updated</b>\nNew prefix: <code>{new_prefix}</code>")

    def get_options(self) -> list[ModuleOption]:
        return [
            ModuleOption(
                key="prefix",
                label="Prefix",
                description="Current command prefix",
                value=self.app.config.prefix,
            )
        ]


module = PrefixModule()
