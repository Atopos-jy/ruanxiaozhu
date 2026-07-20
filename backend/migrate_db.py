"""
数据库迁移脚本：导出原数据库数据 → SQL 文件，或从 SQL 文件导入到目标数据库。

用法:
    # 导出原数据库（.env 中配置的 DATABASE_URL）到 dump.sql
    python migrate_db.py export dump.sql

    # 从 dump.sql 导入到目标数据库
    python migrate_db.py import dump.sql --target postgresql://user:pass@host:5432/dbname

    # 直接迁移（从源库复制到目标库，不需要中间文件）
    python migrate_db.py copy --target postgresql://user:pass@host:5432/dbname
"""

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

# 修复 Windows GBK 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from psycopg import Connection, connect
from psycopg.rows import dict_row

from config import DATABASE_URL


TABLES = [
    {
        "name": "users",
        "columns": ["id", "email", "password_hash", "created_at", "last_login_at"],
    },
    {
        "name": "revoked_tokens",
        "columns": ["jti", "expires_at", "revoked_at"],
    },
    {
        "name": "auth_sessions",
        "columns": [
            "id", "user_id", "refresh_jti",
            "created_at", "expires_at", "refresh_expires_at", "revoked_at",
        ],
    },
    {
        "name": "conversations",
        "columns": ["id", "user_id", "agent_id", "title", "created_at", "updated_at"],
    },
    {
        "name": "messages",
        "columns": ["id", "conversation_id", "role", "content", "tool_calls", "created_at"],
    },
]


def _serialize(value: Any) -> str:
    """Convert a Python value to a SQL literal string."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (datetime,)):
        return f"'{value.isoformat()}'::timestamptz"
    if isinstance(value, (UUID,)):
        return f"'{value}'::uuid"
    if isinstance(value, (dict, list)):
        return f"'{json.dumps(value, ensure_ascii=False)}'::jsonb"
    # string — escape single quotes
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def export_db(output_path: str) -> None:
    """导出原数据库到 SQL 文件。"""
    conn = connect(DATABASE_URL, row_factory=dict_row)
    cursor = conn.cursor()

    lines: list[str] = [
        "-- ============================================================",
        f"-- 软小筑 AI 管家 — 数据库导出",
        f"-- 导出时间: {datetime.now(timezone.utc).isoformat()}",
        f"-- 源数据库: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}",
        "-- ============================================================",
        "",
        "BEGIN;",
        "",
        "-- 启用 pgvector 扩展",
        "CREATE EXTENSION IF NOT EXISTS vector;",
        "",
    ]

    for table in TABLES:
        table_name = table["name"]
        columns = table["columns"]
        col_list = ", ".join(columns)

        cursor.execute(f"SELECT {col_list} FROM {table_name} ORDER BY 1")
        rows: list[dict] = cursor.fetchall()

        lines.append(f"-- ==================== {table_name} ({len(rows)} rows) ====================")
        lines.append("")

        if not rows:
            lines.append(f"-- (empty table)")
            lines.append("")
            continue

        for row in rows:
            values = ", ".join(_serialize(row[col]) for col in columns)
            lines.append(f"INSERT INTO {table_name} ({col_list}) VALUES ({values});")

        lines.append("")
        # Reset sequence-like state if applicable — PostgreSQL UUIDs don't need this
        lines.append("")

    lines.append("COMMIT;")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ 导出完成 → {output_path}")
    print(f"   共导出 {sum(1 for t in TABLES for _ in [1])} 张表")
    for table in TABLES:
        cursor.execute(f"SELECT COUNT(*) as c FROM {table['name']}")
        count = cursor.fetchone()["c"]
        print(f"   {table['name']}: {count} 行")

    conn.close()


def import_db(input_path: str, target_url: str) -> None:
    """从 SQL 文件导入到目标数据库。"""
    with open(input_path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = connect(target_url)
    cursor = conn.cursor()

    try:
        # 先建表
        from database import init_database as _unused
        # We need to import init_database but it uses the original DATABASE_URL,
        # so we manually create tables on the target
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL, last_login_at TIMESTAMPTZ)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti UUID PRIMARY KEY, expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ NOT NULL)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS auth_sessions (
            id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id), refresh_jti UUID NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
            refresh_expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id),
            agent_id TEXT NOT NULL, title TEXT,
            created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY, conversation_id UUID NOT NULL REFERENCES conversations(id),
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
            content TEXT NOT NULL, tool_calls JSONB,
            created_at TIMESTAMPTZ NOT NULL)""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id, created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations (user_id, updated_at DESC)")

        # 执行导入 SQL（按顺序逐表执行，确保外键正确）
        cursor.execute(sql)
        conn.commit()
        print(f"✅ 导入完成 ← {input_path}")
        print(f"   目标: {target_url.split('@')[1] if '@' in target_url else target_url}")
    except Exception as e:
        conn.rollback()
        print(f"❌ 导入失败: {e}")
        raise
    finally:
        conn.close()


def copy_db(target_url: str, source_url: str | None = None) -> None:
    """直接从源数据库复制到目标数据库（不需要中间 SQL 文件）。"""
    src = source_url or DATABASE_URL
    source_conn = connect(src, row_factory=dict_row)
    target_conn = connect(target_url)
    source_cur = source_conn.cursor()
    target_cur = target_conn.cursor()

    try:
        # 目标库建表
        target_cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        target_cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL, last_login_at TIMESTAMPTZ)""")
        target_cur.execute("""CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti UUID PRIMARY KEY, expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ NOT NULL)""")
        target_cur.execute("""CREATE TABLE IF NOT EXISTS auth_sessions (
            id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id), refresh_jti UUID NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
            refresh_expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ)""")
        target_cur.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id),
            agent_id TEXT NOT NULL, title TEXT,
            created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL)""")
        target_cur.execute("""CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY, conversation_id UUID NOT NULL REFERENCES conversations(id),
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
            content TEXT NOT NULL, tool_calls JSONB,
            created_at TIMESTAMPTZ NOT NULL)""")
        target_cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id, created_at)")
        target_cur.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations (user_id, updated_at DESC)")

        # 按依赖顺序逐表复制（先 users，再 auth_sessions/conversations，最后 messages）
        for table in TABLES:
            table_name = table["name"]
            columns = table["columns"]
            col_list = ", ".join(columns)
            placeholders = ", ".join(["%s"] * len(columns))

            source_cur.execute(f"SELECT {col_list} FROM {table_name}")
            rows = source_cur.fetchall()

            if not rows:
                print(f"   {table_name}: 0 行（跳过）")
                continue

            for row in rows:
                values = [row[col] for col in columns]
                target_cur.execute(
                    f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})",
                    values,
                )

            print(f"   {table_name}: {len(rows)} 行已复制")

        target_conn.commit()
        print(f"\n✅ 直接迁移完成")
        print(f"   目标: {target_url.split('@')[1] if '@' in target_url else target_url}")
    except Exception as e:
        target_conn.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        source_conn.close()
        target_conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="软小筑数据库迁移工具")
    sub = parser.add_subparsers(dest="command", required=True)

    export_p = sub.add_parser("export", help="导出数据库到 SQL 文件")
    export_p.add_argument("output", help="输出文件路径，如 dump.sql")

    import_p = sub.add_parser("import", help="从 SQL 文件导入到目标数据库")
    import_p.add_argument("input", help="SQL 文件路径")
    import_p.add_argument("--target", required=True, help="目标数据库 URL")

    copy_p = sub.add_parser("copy", help="直接从源库复制到目标库")
    copy_p.add_argument("--source", help="源数据库 URL（默认使用 .env 中的 DATABASE_URL）")
    copy_p.add_argument("--target", required=True, help="目标数据库 URL")

    args = parser.parse_args()

    if args.command == "export":
        export_db(args.output)
    elif args.command == "import":
        import_db(args.input, args.target)
    elif args.command == "copy":
        copy_db(args.target, source_url=args.source)


if __name__ == "__main__":
    main()
