import asyncio
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, patch

from test_record_source import help_query


class HelpImageTests(unittest.TestCase):
    def test_markdown_is_rendered_with_tables_and_inline_code(self):
        html = help_query.renderHelpHTML()
        self.assertIn("<table>", html)
        self.assertIn("<code>chuconst 15 rin</code>", html)
        self.assertIn("<h1>CHUNITHM Utils</h1>", html)
        self.assertIn("data:font/ttf;base64,", html)

    def test_help_replies_with_one_image_and_reuses_cache(self):
        ctx = types.SimpleNamespace(reply=AsyncMock())
        with tempfile.TemporaryDirectory() as directory:
            async def render(html, output, **kwargs):
                from PIL import Image
                Image.new("RGB", (10, 10), "white").save(output, format="PNG")

            with patch.object(help_query, "HELP_CACHE_DIR", Path(directory)), \
                 patch.object(help_query, "renderHelpHTML", return_value="help document"), \
                 patch.object(help_query, "convertHTMLtoIMG", new=AsyncMock(side_effect=render)) as renderer:
                asyncio.run(help_query.queryHelp(ctx))
                asyncio.run(help_query.queryHelp(ctx))
                renderer.assert_awaited_once()
                self.assertEqual(ctx.reply.await_args.args[0], ["image"])
                self.assertEqual(len(list(Path(directory).glob("help-*.png"))), 1)

    def test_document_changes_replace_old_cached_image(self):
        ctx = types.SimpleNamespace(reply=AsyncMock())
        with tempfile.TemporaryDirectory() as directory:
            async def render(html, output, **kwargs):
                from PIL import Image
                Image.new("RGB", (10, 10), "white").save(output, format="PNG")

            with patch.object(help_query, "HELP_CACHE_DIR", Path(directory)), \
                 patch.object(help_query, "renderHelpHTML", side_effect=["first", "updated"]), \
                 patch.object(help_query, "convertHTMLtoIMG", new=AsyncMock(side_effect=render)) as renderer:
                asyncio.run(help_query.queryHelp(ctx))
                asyncio.run(help_query.queryHelp(ctx))
                self.assertEqual(renderer.await_count, 2)
                self.assertEqual(len(list(Path(directory).glob("help-*.png"))), 1)
                self.assertFalse(list(Path(directory).glob(".help-*.png")))

    def test_old_help_gives_merge_notice_without_rendering_image(self):
        ctx = types.SimpleNamespace(reply=AsyncMock())
        with patch.object(help_query, "convertHTMLtoIMG", new=AsyncMock()) as renderer:
            asyncio.run(help_query.queryLegacyHelp(ctx))
            renderer.assert_not_awaited()
        text = ctx.reply.await_args.args[0][0]
        self.assertIn("已合并到 ChunithmUtil", text)
        self.assertIn("chuhelp", text)

    def test_frozen_unbind_points_to_rebinding_and_new_help(self):
        ctx = types.SimpleNamespace(reply=AsyncMock())
        asyncio.run(help_query.queryLegacyHelp(ctx, unbind=True))
        text = ctx.reply.await_args.args[0][0]
        self.assertIn("unbind 已停用", text)
        self.assertIn("chubind [服务器] [TOKEN]", text)
        self.assertIn("chuhelp", text)


if __name__ == "__main__":
    unittest.main()
