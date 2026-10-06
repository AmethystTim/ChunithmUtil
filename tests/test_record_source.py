"""来源迁移、实际成绩写入入口和 B30 列布局的回归测试。"""

import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import PIL.Image

# 先初始化 Pillow 插件，避免下方 sys.modules 隔离把图片格式注册模块移除。
PIL.Image.init()


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "_chunithm_source_tests"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "src")]
context = types.ModuleType("pkg.plugin.context")
context.EventContext = object
events = types.ModuleType("pkg.plugin.events")
platform = types.ModuleType("pkg.platform.types")
platform.Plain = lambda text: text
platform.MessageChain = list
platform.Image = types.SimpleNamespace(from_local=AsyncMock(return_value="image"))
song = types.ModuleType(f"{PACKAGE}.query_song")
song.searchSong = Mock(return_value=["1"])
api = types.ModuleType(f"{PACKAGE}.utils.apicaller")
api.MsgPlatform = Mock()


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


with patch.dict(sys.modules, {
    PACKAGE: package,
    "pkg.plugin.context": context,
    "pkg.plugin.events": events,
    "pkg.platform.types": platform,
    f"{PACKAGE}.query_song": song,
    f"{PACKAGE}.utils.apicaller": api,
}), patch.dict(os.environ, {"SONG_PATH": "data/test-songs.json"}):
    recorddb = load_module(f"{PACKAGE}.utils.recorddb", "src/utils/recorddb.py")
    imageutil = load_module(f"{PACKAGE}.utils.imageutil", "src/utils/imageutil.py")
    copy = load_module(f"{PACKAGE}.query_copy", "src/query_copy.py")
    upd = load_module(f"{PACKAGE}.query_updscore", "src/query_updscore.py")
    best = load_module(f"{PACKAGE}.query_querybest", "src/query_querybest.py")
    version = load_module(f"{PACKAGE}.query_version", "src/query_version.py")
    renderer = load_module(f"{PACKAGE}.utils.progress_renderer", "src/utils/progress_renderer.py")
    prog = load_module(f"{PACKAGE}.query_prog", "src/query_prog.py")
    help_query = load_module(f"{PACKAGE}.query_help", "src/query_help.py")
    chartutil = load_module(f"{PACKAGE}.utils.chartutil", "src/utils/chartutil.py")
    wechartutil = load_module(f"{PACKAGE}.utils.wechartutil", "src/utils/wechartutil.py")
    chart_query = load_module(f"{PACKAGE}.query_chart", "src/query_chart.py")
    wechart_query = load_module(f"{PACKAGE}.query_wechart", "src/query_wechart.py")


class RecordSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = str(Path(self.temp.name) / "data.db")
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "CREATE TABLE record (user_id TEXT, cid TEXT, score INTEGER, "
                "difficulty INTEGER, PRIMARY KEY (user_id, cid, difficulty))"
            )
            conn.executemany(
                "INSERT INTO record VALUES (?, ?, ?, ?)",
                [("legacy", "1", 1000000, 3), ("legacy", "1", 990000, 2)],
            )
        for module in (copy, upd, best, prog):
            patcher = patch.object(module, "DB_PATH", self.db)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.ctx = types.SimpleNamespace(
            event=types.SimpleNamespace(
                sender_id="user", launcher_id="group",
                query=types.SimpleNamespace(message_event=types.SimpleNamespace(
                    sender=types.SimpleNamespace(get_name=lambda: "test user")
                )),
            ),
            reply=AsyncMock(),
        )

    def rows(self):
        with sqlite3.connect(self.db) as conn:
            return conn.execute("SELECT * FROM record ORDER BY user_id, cid, difficulty, source").fetchall()

    def row_for(self, source, user_id="user", difficulty=3):
        return next(row for row in self.rows() if row[0] == user_id and row[3] == difficulty and row[4] == source)

    def test_migration_preserves_legacy_records_and_is_idempotent(self):
        with sqlite3.connect(self.db) as conn:
            before = conn.execute("SELECT * FROM record ORDER BY user_id, cid, difficulty").fetchall()
        recorddb.migrate_record_source(self.db)
        recorddb.migrate_record_source(self.db)
        after = self.rows()
        self.assertEqual([row[:4] for row in after], before)
        self.assertEqual([row[4] for row in after], ["unknown", "unknown"])
        with sqlite3.connect(self.db) as conn:
            source = next(row for row in conn.execute("PRAGMA table_info(record)") if row[1] == "source")
            key = [row[1] for row in sorted(conn.execute("PRAGMA table_info(record)"), key=lambda row: row[5]) if row[5]]
        self.assertEqual(source[1:3], ("source", "TEXT"))
        self.assertEqual(key, ["user_id", "cid", "difficulty", "source"])
        self.assertTrue(all(row[5:] == (None, None) for row in after))

    def test_each_server_writes_its_own_source(self):
        for server, handler in [("lx", copy.LXHandler), ("rin", copy.RinHandler),
                                ("shiro", copy.ShiroHandler)]:
            with self.subTest(server=server):
                self.assertEqual(handler(self.ctx).updateRecord(server, "1", 1000000, 3), 1)
        self.assertEqual({row[0]: row[4] for row in self.rows() if row[0] != "legacy"},
                         {"lx": "lx", "rin": "rin", "shiro": "shiro"})

    def test_each_source_compares_only_its_own_score(self):
        for handler in (copy.LXHandler, copy.RinHandler, copy.ShiroHandler):
            with self.subTest(handler=handler.__name__):
                upd.updateScore("user", "1", 1000000, 3, "Test Song")
                importer = handler(self.ctx)
                self.assertEqual(importer.updateRecord("user", "1", 999999, 3), 1)
                self.assertEqual(importer.updateRecord("user", "1", 999999, 3), 0)
                self.assertEqual(importer.updateRecord("user", "1", 999998, 3), 0)
                self.assertEqual(self.row_for("manual")[2], 1000000)
                self.assertEqual(importer.updateRecord("user", "1", 1000001, 3), 1)
                server = {
                    copy.LXHandler: "lx", copy.RinHandler: "rin", copy.ShiroHandler: "shiro",
                }[handler]
                self.assertEqual(self.row_for(server)[2], 1000001)

    def test_manual_update_preserves_imported_source_even_with_lower_score(self):
        copy.LXHandler(self.ctx).updateRecord("user", "1", 1000000, 3)
        status, _ = upd.updateScore("user", "1", 999999, 3, "Test Song")
        self.assertEqual(status, 0)
        self.assertEqual(self.row_for("manual"), ("user", "1", 999999, 3, "manual", None, None))
        self.assertEqual(self.row_for("lx")[2], 1000000)
        self.assertEqual(recorddb.load_records(self.db, "user")[0]["score"], 1000000)

    def test_manual_command_records_manual_source(self):
        songs_path = Path(self.temp.name) / "songs.json"
        songs_path.write_text(json.dumps([{"idx": "1", "title": "Test Song", "diff": "master"}]))
        with patch.object(upd, "SONGS_PATH", str(songs_path)):
            asyncio.run(upd.queryUpdScore(self.ctx, ["1000000", "Test Song", None]))
        self.assertEqual(self.row_for("manual"), ("user", "1", 1000000, 3, "manual", None, None))
        self.ctx.reply.assert_awaited_once()

    def test_separate_users_and_difficulties_keep_their_sources(self):
        copy.LXHandler(self.ctx).updateRecord("user", "1", 1000000, 3)
        copy.RinHandler(self.ctx).updateRecord("user", "1", 999000, 2)
        copy.ShiroHandler(self.ctx).updateRecord("other", "1", 998000, 3)
        self.assertEqual({(row[0], row[3]): row[4] for row in self.rows()}, {
            ("legacy", 2): "unknown", ("legacy", 3): "unknown",
            ("user", 2): "rin", ("user", 3): "lx", ("other", 3): "shiro",
        })

    def test_failed_write_rolls_back_migration_and_preserves_records(self):
        with sqlite3.connect(self.db) as conn:
            before = conn.execute("SELECT * FROM record ORDER BY user_id, cid, difficulty").fetchall()
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "CREATE TRIGGER reject_failed_record BEFORE INSERT ON record "
                "WHEN NEW.cid = 'fail' BEGIN SELECT RAISE(ABORT, 'test failure'); END"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            recorddb.save_record(self.db, "user", "fail", 1000000, 3, "manual")
        with sqlite3.connect(self.db) as conn:
            after = conn.execute("SELECT * FROM record ORDER BY user_id, cid, difficulty").fetchall()
        self.assertEqual(after, before)
        upd.updateScore("user", "1", 1000000, 3, "Test Song")
        self.assertEqual(self.rows()[-1][4], "manual")

    def test_b30_simple_handles_unknown_and_manual_sources(self):
        upd.updateScore("user", "1", 1000000, 3, "Test Song")
        copy.RinHandler(self.ctx).updateRecord("user", "1", 999000, 3)
        with patch.object(best, "getSongInfo", return_value=(
            np.array([14.0]), np.array(["Test Song"]), None,
        )), patch.object(best, "MsgPlatform") as message_platform:
            message_platform.return_value.callApi = AsyncMock()
            asyncio.run(best.queryBest30(self.ctx, "user", use_simple=True))
            payload = message_platform.return_value.callApi.await_args.args[1]
        self.assertIn("c1 - Test Song\nmaster\n1000000 -", payload["messages"][0]["data"]["content"][0]["data"]["text"])
        self.assertEqual(len(payload["messages"]), 1)
        # 查询旧成绩也必须保留四列布局，即使 source 为 unknown。
        with patch.object(best, "getSongInfo", return_value=(
            np.array([14.0, 12.0]), np.array(["Test Song", "Test Song"]), None,
        )), patch.object(best, "MsgPlatform") as message_platform:
            message_platform.return_value.callApi = AsyncMock()
            asyncio.run(best.queryBest30(self.ctx, "legacy", use_simple=True))
            payload = message_platform.return_value.callApi.await_args.args[1]
        self.assertEqual(len(payload["messages"]), 2)

    def test_b30_image_keeps_song_name_and_card_layout(self):
        upd.updateScore("user", "1", 1000000, 3, "Test Song")
        songs_path = Path(self.temp.name) / "songs.json"
        songs_path.write_text(json.dumps([{"idx": "1", "img": "cover"}]))
        with patch.object(best, "SONGS_PATH", str(songs_path)), \
             patch.object(best, "getSongInfo", return_value=(
                 np.array([14.0]), np.array(["Test Song"]), None,
             )), patch.object(best, "resolveBestCovers", new=AsyncMock(return_value=["cover.webp"])), \
             patch.object(best, "renderCardHTML", wraps=best.renderCardHTML) as cards, \
             patch.object(best, "renderBestHTML", return_value="html"), \
             patch.object(best, "convertHTMLtoIMG", new=AsyncMock()), \
             patch.object(best, "image_for_send", new=AsyncMock(return_value="image")):
            asyncio.run(best.queryBest30(self.ctx, "user"))
        card = cards.call_args.args[0][0]
        self.assertEqual(len(card), 7)
        self.assertEqual(card[3], "Test Song")
        self.assertEqual(card[-1], "cover.webp")
        self.ctx.reply.assert_awaited_once_with(["image"])


if __name__ == "__main__":
    unittest.main()
