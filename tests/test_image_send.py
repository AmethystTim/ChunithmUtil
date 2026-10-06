import asyncio
import base64
from io import BytesIO
import json
from pathlib import Path
import random
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, patch

from PIL import Image

import test_record_source as fixtures


class ImageSendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "chart.png"
        # 高熵图像验证 JPEG 真正缩小体积，而非只验证改扩展名。
        pixels = random.Random(1).randbytes(240 * 180 * 3)
        Image.frombytes("RGB", (240, 180), pixels).save(self.source, format="PNG")
        self.original = self.source.read_bytes()

    def test_jpeg_is_smaller_keeps_resolution_and_does_not_modify_png(self):
        data, suffix = fixtures.imageutil.encode_image_for_send(str(self.source))
        self.assertEqual(suffix, ".jpg")
        self.assertLess(len(data), len(self.original))
        with Image.open(BytesIO(data)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (240, 180))
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(list(Path(self.temp.name).glob("*.jpg")), [])

    def test_small_flat_png_is_kept_if_jpeg_would_be_larger(self):
        Image.new("RGB", (20, 20), "white").save(self.source, format="PNG")
        original = self.source.read_bytes()
        data, suffix = fixtures.imageutil.encode_image_for_send(str(self.source))
        self.assertEqual((data, suffix), (original, ".png"))

    def test_transparency_is_composited_on_white_for_jpeg(self):
        image = Image.open(self.source).convert("RGBA")
        image.paste((0, 0, 0, 0), (0, 0, 100, 100))
        image.save(self.source, format="PNG")
        original = self.source.read_bytes()
        data, suffix = fixtures.imageutil.encode_image_for_send(str(self.source))
        self.assertEqual(suffix, ".jpg")
        with Image.open(BytesIO(data)) as sent:
            self.assertTrue(all(channel > 245 for channel in sent.getpixel((20, 20))))
        self.assertEqual(self.source.read_bytes(), original)

    def test_platform_image_is_created_from_compressed_bytes(self):
        with patch.object(fixtures.imageutil.Image, "from_local", new=AsyncMock(return_value="sent image")) as loader:
            result = asyncio.run(fixtures.imageutil.image_for_send(str(self.source)))
        self.assertEqual(result, "sent image")
        data = loader.await_args.kwargs["content"]
        with Image.open(BytesIO(data)) as image:
            self.assertEqual(image.format, "JPEG")
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_downloaded_normal_and_we_charts_upload_jpeg_with_correct_filename(self):
        for module, cls, args in (
            (fixtures.chartutil, fixtures.chartutil.ChartUtil, ("mas",)),
            (fixtures.wechartutil, fixtures.wechartutil.WEChartUtil, ("嘘", 3)),
        ):
            with self.subTest(cls=cls.__name__), patch.object(module, "MsgPlatform") as api:
                api.return_value.callApi = AsyncMock(return_value={"data": {"file": "/remote/chart.jpg"}})
                asyncio.run(cls().sendChart(str(self.source), "group", {"idx": "1", "title": "Test Song"}, *args))
                calls = api.return_value.callApi.await_args_list
                self.assertEqual(calls[0].args[0], "/download_file")
                payload = calls[0].args[1]
                self.assertEqual(payload["name"], "chart.jpg")
                with Image.open(BytesIO(base64.b64decode(payload["base64"]))) as image:
                    self.assertEqual(image.format, "JPEG")
                self.assertEqual(calls[1].args[0], "/send_group_msg")
                self.assertEqual(self.source.read_bytes(), self.original)

    def test_cached_normal_chart_uses_compressed_send_path(self):
        songs = Path(self.temp.name) / "songs.json"
        songs.write_text(json.dumps([{"idx": "1", "title": "Test Song", "diff": "MAS"}]))
        ctx = types.SimpleNamespace(reply=AsyncMock())
        with patch.object(fixtures.chart_query, "SONGS_PATH", str(songs)), \
             patch.object(fixtures.chart_query, "CHART_CACHE_DIR", self.temp.name), \
             patch.object(fixtures.chart_query, "ChartUtil") as charts, \
             patch.object(fixtures.chart_query, "image_for_send", new=AsyncMock(return_value="image")) as send:
            charts.return_value.getChartID.return_value = "1"
            charts.return_value.checkIsHit.return_value = True
            asyncio.run(fixtures.chart_query.queryChart(ctx, ["c1", "mas"]))
        send.assert_awaited_once_with(str(Path(self.temp.name) / "1_.png"))
        ctx.reply.assert_awaited_once()

    def test_progress_renderer_overwrites_stable_lossless_cache(self):
        entry = {"id": "1", "score": 1000000, "level_value": 15.2,
                 "level_index": 3, "full_combo": None, "cover_path": str(self.source)}
        with patch.object(fixtures.renderer, "OUTPUT_DIR", Path(self.temp.name)):
            renderer = fixtures.renderer.ProgressRenderer()
            first = renderer.drawImg([entry], "15 RIN", "user", "const")
            entry["score"] = 1009000
            second = renderer.drawImg([entry], "15 RIN", "user", "const")
        self.assertEqual(first, second)
        with Image.open(first) as image:
            self.assertEqual(image.format, "PNG")
        self.assertEqual(len(list(Path(self.temp.name).glob("*.png"))), 2)
        self.assertFalse(list(Path(self.temp.name).glob(".*.png")))


if __name__ == "__main__":
    unittest.main()
