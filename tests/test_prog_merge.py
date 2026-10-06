import ast
import asyncio
import json
from pathlib import Path
import re
import sqlite3
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

import test_record_source as fixtures
from test_record_source import ROOT, copy, help_query, prog, recorddb, upd, version


def chart(cid="1", difficulty="MAS", level=15, const=15.2, generation="SUN"):
    return {"idx": cid, "diff": difficulty, "level": level, "const": const,
            "version": generation, "title": "Test Song", "img": "cover"}


class MergeTests(unittest.TestCase):
    setUp = fixtures.RecordSourceTests.setUp
    rows = fixtures.RecordSourceTests.rows
    row_for = fixtures.RecordSourceTests.row_for

    def save(self, source, score, fc=None, aj=None, cid="1", difficulty=3):
        return recorddb.save_record(self.db, "user", cid, score, difficulty, source,
                                    only_if_higher=source != "manual",
                                    is_full_combo=fc, is_all_justice=aj)

    def test_real_payload_flag_types(self):
        cases = [
            ("lx", {"full_combo": None}, (0, 0)),
            ("lx", {"full_combo": "fullcombo"}, (1, 0)),
            ("lx", {"full_combo": "alljustice"}, (1, 1)),
            ("lx", {}, (None, None)),
            ("rin", {"isFullCombo": "false", "isAllJustice": "false"}, (0, 0)),
            ("rin", {"isFullCombo": "true", "isAllJustice": "false"}, (1, 0)),
            ("rin", {"isFullCombo": "true", "isAllJustice": "true"}, (1, 1)),
            ("shiro", {"isFullCombo": False, "isAllJustice": False}, (0, 0)),
            ("shiro", {"isFullCombo": True, "isAllJustice": True}, (1, 1)),
            ("shiro", {"isAllJustice": True}, (1, 1)),
            ("rin", {}, (None, None)),
        ]
        for source, payload, expected in cases:
            with self.subTest(source=source, payload=payload):
                self.assertEqual(recorddb.record_flags(payload, source), expected)

    def test_lower_or_equal_score_can_add_achievements_without_lowering_score(self):
        self.save("shiro", 1009000, 0, 0)
        self.assertEqual(self.save("shiro", 1008000, 1, 1), 1)
        self.assertEqual(self.row_for("shiro")[2:], (1009000, 3, "shiro", 1, 1))
        self.assertEqual(self.save("shiro", 1009000, 0, 0), 0)
        self.assertEqual(self.save("shiro", 1009000), 0)

    def test_unknown_does_not_block_new_server_record(self):
        recorddb.migrate_record_source(self.db)
        before = next(row for row in self.rows() if row[0] == "legacy" and row[3] == 3)
        self.assertEqual(copy.ShiroHandler(self.ctx).updateRecord("legacy", "1", 999999, 3), 1)
        self.assertEqual(self.row_for("shiro", "legacy")[2], 999999)
        self.assertEqual(self.row_for("unknown", "legacy"), before)

    def test_all_sources_take_max_score_and_independent_achievements(self):
        self.save("manual", 1009000)
        self.save("lx", 1000000, 1, 1)
        self.save("rin", 999000, 0, 0)
        result = recorddb.load_records(self.db, "user")[0]
        self.assertEqual((result["score"], result["is_full_combo"], result["is_all_justice"]),
                         (1009000, 1, 1))
        rin = recorddb.load_records(self.db, "user", "rin")[0]
        self.assertEqual((rin["score"], rin["is_all_justice"]), (999000, 0))

    def test_ajc_requires_confirmed_theory_score_in_one_source(self):
        self.save("manual", 1010000)
        self.save("rin", 1008000, 1, 1)
        entries = prog.prog_entries([chart()], recorddb.load_records(self.db, "user"), "SUN")
        self.assertEqual(prog.badge_count(entries, "aj"), 1)
        self.assertEqual(prog.badge_count(entries, "ajc"), 0)
        self.save("shiro", 1010000, 1, 1)
        entries = prog.prog_entries([chart()], recorddb.load_records(self.db, "user"), "SUN")
        self.assertEqual(prog.badge_count(entries, "ajc"), 1)

    def test_manual_and_unknown_cannot_be_selected(self):
        for source in ("manual", "unknown"):
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    recorddb.load_records(self.db, "user", source)
                with self.assertRaises(ValueError):
                    prog.parse_prog_args("sun aj " + source)
                self.ctx.reply.reset_mock()
                asyncio.run(prog.queryConst(self.ctx, ["15", source]))
                self.assertIn("仅支持 lx", self.ctx.reply.await_args.args[0][0])

    def test_const_matches_displayed_level_and_all_difficulties(self):
        self.save("rin", 1000000, cid="1", difficulty=3)
        self.save("rin", 999000, cid="2", difficulty=2)
        self.save("rin", 998000, cid="3", difficulty=4)
        charts = [chart(), chart("2", "EXP", 15, 15.0), chart("3", "ULT", 15.5, 15.7), chart("4")]
        records = recorddb.load_records(self.db, "user", "rin")
        self.assertEqual({row["id"] for row in prog.const_entries(charts, records, "15")}, {"1", "2"})
        self.assertEqual([row["id"] for row in prog.const_entries(charts, records, "15+")], ["3"])

    def test_prog_includes_unplayed_master_but_excludes_other_versions_and_ultima(self):
        self.save("rin", 1007500)
        charts = [chart(), chart("2"), chart("3", "ULT"), chart("4", generation="AIR")]
        entries = prog.prog_entries(charts, recorddb.load_records(self.db, "user"), "SUN")
        self.assertEqual([row["score"] for row in entries], [1007500, 0])
        self.assertEqual(prog.badge_count(entries, "sss"), 1)

    def test_badge_score_boundaries(self):
        entries = [dict(score=score, is_all_justice=None, is_all_justice_critical=0)
                   for score in (974999, 975000, 1007499, 1007500, 1008999, 1009000)]
        self.assertEqual(prog.badge_count(entries, "s"), 5)
        self.assertEqual(prog.badge_count(entries, "sss"), 3)
        self.assertEqual(prog.badge_count(entries, "sss+"), 1)
        self.assertEqual(prog.badge_count(entries, "aj"), 0)

    def test_command_arguments_support_default_badge_server_and_multiword_versions(self):
        cases = {
            "sun": ("sun", "sss", None),
            "sun rin": ("sun", "sss", "rin"),
            "sun aj shiro": ("sun", "aj", "shiro"),
            "SUN SSS+ LX": ("SUN", "sss+", "lx"),
            "SUN PLUS rin": ("SUN PLUS", "sss", "rin"),
            "CHUNITHM SUN PLUS aj rin": ("SUN PLUS", "aj", "rin"),
            "无印 shiro": ("无印", "sss", "shiro"),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(prog.parse_prog_args(text), expected)

    def test_const_command_filters_server_and_defaults_to_all_sources(self):
        self.save("manual", 1009000)
        self.save("rin", 999000)
        with patch.object(prog, "_charts", return_value=[chart()]), \
             patch.object(prog, "_send_chart", new=AsyncMock()) as send:
            asyncio.run(prog.queryConst(self.ctx, ["15", "rin"]))
            self.assertEqual(send.await_args.args[1][0]["score"], 999000)
            asyncio.run(prog.queryConst(self.ctx, ["15", None]))
            self.assertEqual(send.await_args.args[1][0]["score"], 1009000)

    def test_prog_command_handles_original_empty_version_name(self):
        self.save("shiro", 1007500)
        with patch.object(prog, "convertVersion", return_value=""), \
             patch.object(prog, "_charts", return_value=[chart(generation="")]), \
             patch.object(prog, "_send_chart", new=AsyncMock()) as send:
            asyncio.run(prog.queryProg(self.ctx, ["无印 shiro"]))
            self.assertIn("无印 将进度：1/1", send.await_args.args[-1])

    def test_prog_command_reports_missing_aj_flags(self):
        self.save("manual", 1010000)
        with patch.object(prog, "convertVersion", return_value="SUN"), \
             patch.object(prog, "_charts", return_value=[chart()]), \
             patch.object(prog, "_send_chart", new=AsyncMock()) as send:
            asyncio.run(prog.queryProg(self.ctx, ["sun aj"]))
            self.assertIn("神进度：0/1", send.await_args.args[-1])
            self.assertIn("AJ 状态未确认", send.await_args.args[-1])

    def test_missing_server_data_prompts_copy_without_api_request(self):
        self.save("manual", 1000000)
        asyncio.run(prog.queryConst(self.ctx, ["15", "rin"]))
        self.assertIn("chucopy rin", self.ctx.reply.await_args.args[0][0])

    def test_lx_import_keeps_full_combo_enum(self):
        handler = copy.LXHandler(self.ctx)
        payload = {"id": 1, "score": 1000000, "level_index": 3, "full_combo": "fullcombo"}
        response = Mock(status_code=200)
        response.json.return_value = {"code": 200, "success": True, "data": [payload]}
        with patch.object(handler, "readUsersJson", new=AsyncMock(return_value={"user": "test-token"})), \
             patch.object(copy.requests, "get", return_value=response):
            asyncio.run(handler.copyLXRecord())
        self.assertEqual(self.row_for("lx")[5:], (1, 0))

    def test_rin_import_converts_string_scores_difficulties_and_flags(self):
        handler = copy.RinHandler(self.ctx)
        payload = {"musicId": "1", "scoreMax": "1000000", "level": "3",
                   "isFullCombo": "false", "isAllJustice": "false"}
        response = {"status": 200, "data": {"userMusicList": [{"userMusicDetailList": [payload]}]}}
        with patch.object(handler, "readUsersJson", new=AsyncMock(return_value={"user": "test-card"})), \
             patch.object(handler, "get_rin_user_music", return_value=response):
            asyncio.run(handler.copyRinRecord())
        self.assertEqual(self.row_for("rin")[2:], (1000000, 3, "rin", 0, 0))

    def test_shiro_import_preserves_boolean_flags(self):
        handler = copy.ShiroHandler(self.ctx)
        payload = {"musicId": 1, "scoreMax": 1010000, "level": 3,
                   "isFullCombo": True, "isAllJustice": True}
        response = {"status": 200, "data": {"userMusicList": [{"userMusicDetailList": [payload]}]}}
        fake_source = Path(self.temp.name) / "src" / "query_copy.py"
        fake_source.parent.mkdir()
        (Path(self.temp.name) / "data").mkdir()
        with patch.object(handler, "readUsersJson", new=AsyncMock(return_value={"user": "test-card"})), \
             patch.object(handler, "get_shiro_user_music", return_value=response), \
             patch.object(copy, "__file__", str(fake_source)):
            asyncio.run(handler.copyShiroRecord())
        self.assertEqual(self.row_for("shiro")[5:], (1, 1))

    def test_current_source_schema_migrates_without_changing_existing_source(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("ALTER TABLE record ADD COLUMN source TEXT NOT NULL DEFAULT 'unknown'")
            conn.execute("UPDATE record SET source = 'shiro'")
        recorddb.migrate_record_source(self.db)
        recorddb.migrate_record_source(self.db)
        self.assertEqual({row[4] for row in self.rows()}, {"shiro"})
        self.assertEqual(len(self.rows()), 2)

    def test_migration_preserves_custom_index_and_trigger(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE INDEX record_user_lookup ON record (user_id)")
            conn.execute("CREATE TRIGGER reject_bad_score BEFORE INSERT ON record "
                         "WHEN NEW.score < 0 BEGIN SELECT RAISE(ABORT, 'bad score'); END")
        recorddb.migrate_record_source(self.db)
        with sqlite3.connect(self.db) as conn:
            schema = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
        self.assertTrue({"record_user_lookup", "reject_bad_score"} <= schema)
        with self.assertRaises(sqlite3.IntegrityError):
            self.save("manual", -1)

    def test_help_includes_examples_defaults_and_frozen_unbind(self):
        text = help_query.HELP_MD_PATH.read_text(encoding="utf-8")
        for value in ("chuconst 15 rin", "chuprog sun aj shiro", "默认 sss", "最高分", "unbind 已停用"):
            self.assertIn(value, text)

    def test_main_dispatch_and_help_aliases_and_frozen_unbind(self):
        tree = ast.parse((ROOT / "main.py").read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        cls.decorator_list = []
        cls.bases = [ast.Name(id="object", ctx=ast.Load())]
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                node.decorator_list = []
        namespace = {"re": re, "os": __import__("os"), "APIHost": object, "EventContext": object,
                     "GuessGame": Mock, "queryConst": AsyncMock(), "queryProg": AsyncMock(),
                     "queryHelp": AsyncMock(), "queryLegacyHelp": AsyncMock(),
                     "parseArgs": lambda regex, text: list(re.match(regex, text).groups())}
        module = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
        exec(compile(module, str(ROOT / "main.py"), "exec"), namespace)
        plugin = namespace[cls.name](None)
        for command in ("chuhelp", "chu help"):
            self.assertEqual(plugin.matchPattern(command), "chu help")
        self.ctx.event.message_chain = "chuprg help"
        asyncio.run(plugin.msg_received(self.ctx))
        namespace["queryLegacyHelp"].assert_awaited_once_with(self.ctx)
        namespace["queryLegacyHelp"].reset_mock()
        self.ctx.event.message_chain = "unbind"
        asyncio.run(plugin.msg_received(self.ctx))
        namespace["queryLegacyHelp"].assert_awaited_once_with(self.ctx, unbind=True)
        self.ctx.event.message_chain = "chuconst 15 rin"
        asyncio.run(plugin.msg_received(self.ctx))
        namespace["queryConst"].assert_awaited_once_with(self.ctx, ["15", "rin"])
        self.ctx.event.message_chain = "chuprog sun aj shiro"
        asyncio.run(plugin.msg_received(self.ctx))
        namespace["queryProg"].assert_awaited_once_with(self.ctx, ["sun aj shiro"])

    def test_send_chart_preserves_lossless_image_and_compresses_for_sending(self):
        output = Path(self.temp.name) / "chart.png"
        output.write_bytes(b"temporary image")
        entries = [prog._entry(chart(), {"score": 1000000}, 3)]
        with patch.object(prog, "resolveBestCovers", new=AsyncMock(return_value=["cover.webp"])), \
             patch.object(prog, "ProgressRenderer") as rendering, \
             patch.object(prog, "image_for_send", new=AsyncMock(return_value="image")) as sending:
            rendering.return_value.drawImg.return_value = str(output)
            asyncio.run(prog._send_chart(self.ctx, entries, "15 RIN", "const", "summary"))
        self.assertEqual(output.read_bytes(), b"temporary image")
        sending.assert_awaited_once_with(str(output))
        self.ctx.reply.assert_awaited_once()

    def test_renderer_uses_migrated_resources_and_fits_many_constant_groups(self):
        rendering = fixtures.renderer
        entries = [prog._entry(chart(str(i), const=9.0 + i * 0.1), {"score": 1000000}, 3)
                   for i in range(50)]
        with patch.object(rendering, "OUTPUT_DIR", Path(self.temp.name)):
            output = rendering.ProgressRenderer().drawImg(entries, "LUMINOUS PLUS ALL SOURCES", "user", "prog")
        from PIL import Image
        with Image.open(output) as image:
            self.assertEqual(image.width, 1460)
            # 50 个分组按实际字体和行数计算高度，不使用每组 300px 的旧估算。
            self.assertGreater(image.height, 15120)

    def test_legacy_version_aliases_and_chunithmutil_aliases_both_work(self):
        for alias, expected in [("amaz", "AMAZON"), ("starplus", "STAR PLUS"),
                                ("sunp", "SUN PLUS"), ("xvx", "X-VERSE-X"), ("无印", "")]:
            with self.subTest(alias=alias):
                self.assertEqual(version.convertVersion(alias), expected)


if __name__ == "__main__":
    unittest.main()
