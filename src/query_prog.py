"""合并 ChuProg 的等级分数表和版本牌子进度，使用本地多来源成绩。"""

import asyncio
import json
import os
from pathlib import Path
import sqlite3

from pkg.plugin.context import EventContext
from pkg.platform.types import MessageChain, Plain, Image

from .query_querybest import resolveBestCovers
from .query_version import convertVersion
from .utils.progress_renderer import ProgressRenderer
from .utils.recorddb import SERVERS, load_records
from .utils.songutil import SongUtil
from .utils.imageutil import image_for_send

PLUGIN_DIR = Path(__file__).resolve().parents[1]
DB_PATH = str(PLUGIN_DIR / "data" / "data.db")
SONGS_PATH = PLUGIN_DIR / os.getenv("SONG_PATH", "data/songs.json")
LEVELS = {str(level) + suffix for level in range(9, 16) for suffix in ("", "+")}
BADGES = {"s": "Spirit牌", "sss": "将", "sss+": "全SSS+", "aj": "神", "ajc": "巫"}


def parse_prog_args(text: str) -> tuple:
    tokens = text.split()
    server = None
    if tokens and tokens[-1].lower() in SERVERS:
        server = tokens.pop().lower()
    if tokens and tokens[-1].lower() in ("manual", "unknown"):
        raise ValueError("服务器仅支持 lx、rin、shiro；省略服务器会查询所有来源")
    badge = tokens.pop().lower() if tokens and tokens[-1].lower() in BADGES else "sss"
    if not tokens:
        raise ValueError("用法：chuprog [版本] [牌子可选] [服务器可选]")
    version = " ".join(tokens)
    if version.upper().startswith("CHUNITHM "):
        version = version[len("CHUNITHM "):]
    elif version.upper() == "CHUNITHM":
        version = "无印"
    return version, badge, server


def _charts():
    with open(SONGS_PATH, encoding="utf-8-sig") as file:
        return json.load(file)


def _entry(chart, record, difficulty):
    fc, aj = record.get("is_full_combo"), record.get("is_all_justice")
    return {
        "id": str(chart["idx"]), "title": chart.get("title"),
        "score": record.get("score", 0), "level_value": chart.get("const"),
        "level_index": difficulty, "img": chart.get("img"),
        "is_full_combo": fc, "is_all_justice": aj,
        "is_all_justice_critical": record.get("is_all_justice_critical", 0),
        "full_combo": "alljustice" if aj == 1 else "fullcombo" if fc == 1 else None,
    }


def const_entries(charts, records, level):
    """等级参数与显示等级匹配，按实际定数分组，涵盖各普通难度。"""
    lookup = {(row["cid"], row["difficulty"]): row for row in records}
    util = SongUtil()
    result = []
    for chart in charts:
        difficulty = util.getDiff2Index(chart.get("diff", ""))
        displayed = chart.get("level")
        if displayed is None or difficulty is None:
            continue
        value = float(displayed)
        label = str(int(value)) + ("+" if value - int(value) >= 0.5 else "")
        record = lookup.get((str(chart["idx"]), difficulty))
        if label == level and record is not None:
            result.append(_entry(chart, record, difficulty))
    return result


def prog_entries(charts, records, version):
    """版本进度仅统计 MASTER；未游玩的谱面保留并计零分。"""
    lookup = {(row["cid"], row["difficulty"]): row for row in records}
    util = SongUtil()
    return [
        _entry(chart, lookup.get((str(chart["idx"]), 3), {}), 3)
        for chart in charts
        if chart.get("version") == version and util.getDiff2Index(chart.get("diff", "")) == 3
    ]


def badge_count(entries, badge):
    if badge == "aj":
        return sum(entry["is_all_justice"] == 1 for entry in entries)
    if badge == "ajc":
        return sum(entry["is_all_justice_critical"] == 1 for entry in entries)
    threshold = {"s": 975000, "sss": 1007500, "sss+": 1009000}[badge]
    return sum(entry["score"] >= threshold for entry in entries)


async def _send_chart(ctx, entries, header, mode, summary):
    paths = await resolveBestCovers([entry["img"] for entry in entries])
    for entry, path in zip(entries, paths):
        entry["cover_path"] = path
    image_path = await asyncio.to_thread(
        ProgressRenderer().drawImg, entries, header, str(ctx.event.sender_id), mode,
    )
    image = await image_for_send(image_path)
    await ctx.reply(MessageChain([Plain(summary + "\n"), image]))


async def _no_records(ctx, server):
    label = f"{server} 服务器" if server else "本地"
    command = f"chucopy {server}" if server else "chucopy [服务器]"
    await ctx.reply(MessageChain([Plain(f"暂无你的{label}成绩，请先使用 {command} 同步游玩记录")]))


async def queryConst(ctx: EventContext, args: list) -> None:
    level = args[0]
    server = args[1].lower() if len(args) > 1 and args[1] else None
    if server is not None and server not in SERVERS:
        await ctx.reply(MessageChain([Plain("服务器仅支持 lx、rin、shiro；省略服务器会查询所有来源")]))
        return
    if level not in LEVELS:
        await ctx.reply(MessageChain([Plain("等级参数不合法，请使用 9、9+…15、15+，例如 chuconst 15 rin")]))
        return
    try:
        records = load_records(DB_PATH, str(ctx.event.sender_id), server)
        if not records:
            await _no_records(ctx, server)
            return
        entries = const_entries(_charts(), records, level)
        if not entries:
            await ctx.reply(MessageChain([Plain(f"{server or '全部来源'}中暂无你的{level}级成绩")]))
            return
        source_label = server.upper() if server else "ALL SOURCES"
        summary = f"{level}级分数表｜{server or '全部来源最高分'}｜共{len(entries)}个谱面"
        await _send_chart(ctx, entries, f"{level} {source_label}", "const", summary)
    except (sqlite3.Error, OSError, ValueError) as error:
        await ctx.reply(MessageChain([Plain(f"查询等级分数表失败：{error}")]))


async def queryProg(ctx: EventContext, args: list) -> None:
    try:
        version_arg, badge, server = parse_prog_args(args[0])
        version = convertVersion(version_arg)
        # 无印版本的标准名称为空字符串，不能用真假值判断。
        if version is None:
            await ctx.reply(MessageChain([Plain("未知版本或参数，请使用 chuprog [版本] [牌子可选] [服务器可选]；服务器支持 lx、rin、shiro")]))
            return
        records = load_records(DB_PATH, str(ctx.event.sender_id), server)
        if not records:
            await _no_records(ctx, server)
            return
        entries = prog_entries(_charts(), records, version)
        if not entries:
            await ctx.reply(MessageChain([Plain(f"{version or '无印'}版本暂无 MASTER 谱面，请检查或更新曲库")]))
            return
        name = version or "无印"
        count = badge_count(entries, badge)
        summary = f"{name} {BADGES[badge]}进度：{count}/{len(entries)}｜{server or '全部来源最高分'}"
        unknown = sum(entry["score"] > 0 and entry["is_all_justice"] is None for entry in entries)
        if badge in ("aj", "ajc") and unknown:
            summary += f"\n{unknown}个已玩谱面的 AJ 状态未确认，请使用 chucopy 同步对应服务器"
        source_label = server.upper() if server else "ALL SOURCES"
        await _send_chart(ctx, entries, f"{version or 'ORIGINAL'} {source_label}", "prog", summary)
    except (sqlite3.Error, OSError, ValueError) as error:
        await ctx.reply(MessageChain([Plain(f"查询版本进度失败：{error}")]))
