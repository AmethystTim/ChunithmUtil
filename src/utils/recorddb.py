"""按来源保存成绩、FC/AJ 状态，并兼容旧成绩数据库。"""

import sqlite3
from contextlib import closing, contextmanager

SERVERS = ("lx", "rin", "shiro")
_COLUMNS = ("user_id", "cid", "score", "difficulty", "source",
            "is_full_combo", "is_all_justice")


def _create_table(conn, name):
    conn.execute(f"""CREATE TABLE {name} (
        user_id TEXT, cid TEXT, score INTEGER, difficulty INTEGER,
        source TEXT NOT NULL DEFAULT 'unknown',
        is_full_combo INTEGER CHECK (is_full_combo IN (0, 1)),
        is_all_justice INTEGER CHECK (is_all_justice IN (0, 1)),
        PRIMARY KEY (user_id, cid, difficulty, source)
    )""")


def _migrate(conn):
    info = conn.execute("PRAGMA table_info(record)").fetchall()
    if not info:
        _create_table(conn, "record")
        return
    columns = {row[1] for row in info}
    primary_key = [row[1] for row in sorted(info, key=lambda row: row[5]) if row[5]]
    if primary_key == ["user_id", "cid", "difficulty", "source"] and set(_COLUMNS) <= columns:
        return
    if columns - set(_COLUMNS):
        raise RuntimeError("record 存在未识别字段，停止迁移以保留数据")
    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE tbl_name = 'record' "
        "AND type IN ('index', 'trigger') AND sql IS NOT NULL"
    ).fetchall()
    _create_table(conn, "record_source_migration")
    expressions = [
        "COALESCE(NULLIF(source, ''), 'unknown')" if name == "source" and name in columns
        else name if name in columns
        else "'unknown'" if name == "source"
        else "NULL"
        for name in _COLUMNS
    ]
    conn.execute(
        "INSERT INTO record_source_migration (" + ", ".join(_COLUMNS) + ") "
        "SELECT " + ", ".join(expressions) + " FROM record"
    )
    conn.execute("DROP TABLE record")
    conn.execute("ALTER TABLE record_source_migration RENAME TO record")
    for (sql,) in schema:
        conn.execute(sql)


@contextmanager
def record_connection(db_path: str):
    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            _migrate(conn)
            yield conn


def migrate_record_source(db_path: str) -> None:
    """幂等迁移；保留旧分数及来源，缺失的 FC/AJ 保持未知。"""
    with record_connection(db_path):
        pass


def _flag(value):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)) and value in (0, 1):
        return int(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "1"):
            return 1
        if normalized in ("false", "0"):
            return 0
    return None


def record_flags(record: dict, source: str) -> tuple:
    """归一化 LX 枚举、Rin 字符串布尔值和 Shiro 布尔值。"""
    if source == "lx":
        if "full_combo" not in record:
            return None, None
        value = record["full_combo"]
        if value == "alljustice":
            return 1, 1
        if value == "fullcombo":
            return 1, 0
        if value is None:
            return 0, 0
        return None, None
    fc, aj = _flag(record.get("isFullCombo")), _flag(record.get("isAllJustice"))
    return (1 if aj == 1 else fc), aj


def _merge_flag(previous, incoming):
    if previous == 1 or incoming == 1:
        return 1
    if previous == 0 or incoming == 0:
        return 0
    return None


def save_record(
    db_path: str, user_id: str, cid: str, score: int, difficulty: int,
    source: str, *, only_if_higher: bool = False,
    is_full_combo=None, is_all_justice=None,
) -> int:
    """来源内保留最高分和已达成状态；manual 可覆盖自己的分数。"""
    score, difficulty = int(score), int(difficulty)
    fc, aj = _flag(is_full_combo), _flag(is_all_justice)
    if aj == 1:
        fc = 1
    with record_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT score, is_full_combo, is_all_justice FROM record "
            "WHERE user_id = ? AND cid = ? AND difficulty = ? AND source = ?",
            (str(user_id), str(cid), difficulty, source),
        ).fetchone()
        if existing and only_if_higher:
            score = max(existing[0], score)
            fc, aj = _merge_flag(existing[1], fc), _merge_flag(existing[2], aj)
            if (score, fc, aj) == existing:
                return 0
        conn.execute(
            "INSERT INTO record (user_id, cid, score, difficulty, source, "
            "is_full_combo, is_all_justice) VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (user_id, cid, difficulty, source) DO UPDATE SET "
            "score = excluded.score, is_full_combo = excluded.is_full_combo, "
            "is_all_justice = excluded.is_all_justice",
            (str(user_id), str(cid), score, difficulty, source, fc, aj),
        )
        return 1


def load_records(db_path: str, user_id: str, source=None) -> list:
    """逐谱面取最高分，FC/AJ 独立合并；source=None 包含所有来源。"""
    if source is not None and source not in SERVERS:
        raise ValueError("服务器仅支持 lx、rin、shiro")
    condition, args = "user_id = ?", [str(user_id)]
    if source is not None:
        condition += " AND source = ?"
        args.append(source)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(
            "SELECT cid, difficulty, MAX(score) AS score, "
            "MAX(is_full_combo) AS is_full_combo, MAX(is_all_justice) AS is_all_justice, "
            "MAX(CASE WHEN score = 1010000 AND is_all_justice = 1 "
            "THEN 1 ELSE 0 END) AS is_all_justice_critical "
            "FROM record WHERE " + condition + " GROUP BY cid, difficulty",
            args,
        )]
