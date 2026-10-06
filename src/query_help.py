"""将 Markdown 帮助文档渲染为图片。"""

import asyncio
import base64
from functools import lru_cache
import hashlib
import os
from pathlib import Path
from uuid import uuid4

from jinja2 import Template
from markdown_it import MarkdownIt

from pkg.plugin.context import EventContext
from pkg.platform.types import Image, MessageChain, Plain

from .query_querybest import convertHTMLtoIMG
from .utils.imageutil import image_for_send

PLUGIN_DIR = Path(__file__).resolve().parents[1]
HELP_MD_PATH = PLUGIN_DIR / "docs" / "help.md"
HELP_TEMPLATE_PATH = PLUGIN_DIR / "template" / "help.html"
HELP_FONT_PATH = PLUGIN_DIR / "assets" / "progress" / "font" / "simhei.ttf"
HELP_CACHE_DIR = PLUGIN_DIR / "cache" / "help"
_HELP_LOCK = asyncio.Lock()


@lru_cache(maxsize=1)
def _font_uri(path: str, modified: int) -> str:
    return "data:font/ttf;base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")


def renderHelpHTML() -> str:
    markdown = HELP_MD_PATH.read_text(encoding="utf-8")
    content = MarkdownIt("commonmark", {"html": False}).enable("table").render(markdown)
    template = Template(HELP_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.render(
        content=content,
        font_uri=_font_uri(str(HELP_FONT_PATH), HELP_FONT_PATH.stat().st_mtime_ns),
    )


async def queryHelp(ctx: EventContext) -> None:
    """返回帮助图片；文档变化后自动更新缓存，所有帮助别名共用。"""
    try:
        html = renderHelpHTML()
        digest = hashlib.sha256(html.encode("utf-8")).hexdigest()[:20]
        async with _HELP_LOCK:
            HELP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            output = HELP_CACHE_DIR / f"help-{digest}.png"
            if not output.is_file():
                temporary = HELP_CACHE_DIR / f".help-{uuid4().hex}.png"
                try:
                    await convertHTMLtoIMG(html, str(temporary), width=1280, height=740)
                    os.replace(temporary, output)
                finally:
                    temporary.unlink(missing_ok=True)
            image = await image_for_send(str(output))
            for previous in HELP_CACHE_DIR.glob("help-*.png"):
                if previous != output:
                    previous.unlink(missing_ok=True)
    except Exception as error:
        print(f"帮助图片生成失败：{error}")
        await ctx.reply(MessageChain([Plain("帮助图片生成失败，请稍后重试")]))
        return
    await ctx.reply(MessageChain([image]))


async def queryLegacyHelp(ctx: EventContext, *, unbind: bool = False) -> None:
    message = "ChuProg 的功能已合并到 ChunithmUtil，请使用 chuhelp 查询帮助指令。"
    if unbind:
        message += "\nunbind 已停用；更换绑定请使用 chubind [服务器] [TOKEN]。"
    await ctx.reply(MessageChain([Plain(message)]))
