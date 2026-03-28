from __future__ import annotations

import asyncio
import contextlib
import io
import os
import traceback
from pathlib import Path
from pyrogram.enums import ParseMode as PyrogramParseMode
from pyrogram.types import InputMediaDocument
from vibe.core import BaseModule, command


class SystemModule(BaseModule):
    name = "system"
    title = "System"
    description = "System commands."

    @command("logs", help_text="Send the full log file.")
    async def logs(self, ctx) -> None:
        await ctx.message.edit_media(
            InputMediaDocument(
                media=str(ctx.app.config.resolved_log_file),
                caption="<b>Vibe Logs</b>",
                parse_mode=PyrogramParseMode.HTML,
                file_name=ctx.app.config.resolved_log_file.name,
            )
        )

    @command("restart", help_text="Restart the VibeUB process.")
    async def restart(self, ctx) -> None:
        await ctx.reply("<b>🔄 Restart</b>\nProcess re-execution requested.")
        ctx.app.request_restart()
        ctx.app.request_shutdown()

    @command("eval", help_text="Evaluate async Python code.")
    async def eval_command(self, ctx) -> None:
        if not ctx.raw_args:
            await ctx.reply("<b>🧠 Eval</b>\nUsage: <code>eval &lt;python code&gt;</code>")
            return

        env = {
            "app": ctx.app,
            "client": ctx.client,
            "message": ctx.message,
            "ctx": ctx,
            "module": self,
            "__builtins__": __builtins__,
        }
        code = "async def __vibe_eval__():\n" + "\n".join(f"    {line}" for line in ctx.raw_args.splitlines())
        stdout = io.StringIO()
        try:
            exec(code, env)
            with contextlib.redirect_stdout(stdout):
                result = await env["__vibe_eval__"]()
        except Exception:
            output = stdout.getvalue()
            trace = traceback.format_exc()
            await ctx.reply(f"<b>❌ Eval Error</b>\n<pre>{output}{trace}</pre>")
            return

        output = stdout.getvalue()
        rendered = output if result is None else f"{output}{result!r}"
        await ctx.reply(f"<b>✅ Eval Result</b>\n<pre>{rendered or 'ok'}</pre>")

    @command("terminal", help_text="Run a shell command: terminal <command>")
    async def terminal(self, ctx) -> None:
        if not ctx.raw_args:
            await ctx.reply("<b>🖥 Terminal</b>\nUsage: <code>terminal &lt;command&gt;</code>")
            return

        process = await asyncio.create_subprocess_shell(
            ctx.raw_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(Path.cwd()),
            env=os.environ.copy(),
        )
        stdout, _ = await process.communicate()
        output = stdout.decode("utf-8", errors="replace").strip()
        rendered = f"$ {ctx.raw_args}\n{output}" if output else f"$ {ctx.raw_args}\n<no output>"
        if len(rendered) <= 3500:
            await ctx.reply(f"<b>🖥 Terminal</b>\n<pre>{rendered}</pre>")
            return

        tmp_path = ctx.app.config.resolved_workdir / "terminal-output.txt"
        tmp_path.write_text(rendered, encoding="utf-8")
        await ctx.message.reply_document(str(tmp_path), caption="terminal output")


module = SystemModule()
