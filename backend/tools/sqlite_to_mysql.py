"""
SQLite → MySQL 数据迁移工具
用法: python sqlite_to_mysql.py <sqlite_db_path> <output_sql_path>
示例: python sqlite_to_mysql.py ./worldcup.db /tmp/worldcup_data.sql
"""

import sqlite3
import json
import sys
import os
import re


def escape_mysql_string(value: str) -> str:
    """MySQL 字符串转义"""
    if value is None:
        return "NULL"
    # 转义反斜杠、单引号、换行、回车
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace("'", "\\'")
    value = value.replace("\n", "\\n")
    value = value.replace("\r", "\\r")
    value = value.replace("\x00", "\\0")
    value = value.replace("\x1a", "\\Z")
    return f"'{value}'"


def format_value(val, col_type: str) -> str:
    """格式化单值为 MySQL SQL 字面量"""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, bytes):
        # BLOB 转 hex
        return "0x" + val.hex()
    if isinstance(val, (dict, list)):
        return escape_mysql_string(json.dumps(val, ensure_ascii=False))
    return escape_mysql_string(str(val))


def get_table_names(conn: sqlite3.Connection) -> list[str]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [row[0] for row in cursor.fetchall()]


def get_table_columns(conn: sqlite3.Connection, table: str) -> list[tuple]:
    """返回 [(name, type), ...]"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info([{table}])")
    return [(row[1], row[2]) for row in cursor.fetchall()]


def count_rows(conn: sqlite3.Connection, table: str) -> int:
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
    return cursor.fetchone()[0]


def export_table(conn: sqlite3.Connection, table: str, f, batch_size: int = 500):
    columns = get_table_columns(conn, table)
    col_names = [c[0] for c in columns]
    col_types = [c[1].upper() for c in columns]
    col_sql = ", ".join(f"`{name}`" for name in col_names)

    total = count_rows(conn, table)
    if total == 0:
        return 0

    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM [{table}]")

    rows_written = 0
    batch_rows = []

    for row in cursor:
        values = []
        for i, val in enumerate(row):
            values.append(format_value(val, col_types[i] if i < len(col_types) else "TEXT"))
        batch_rows.append(f"({', '.join(values)})")
        rows_written += 1

        if len(batch_rows) >= batch_size:
            f.write(f"INSERT IGNORE INTO `{table}` ({col_sql}) VALUES\n")
            f.write(",\n".join(batch_rows))
            f.write(";\n\n")
            batch_rows = []

    if batch_rows:
        f.write(f"INSERT IGNORE INTO `{table}` ({col_sql}) VALUES\n")
        f.write(",\n".join(batch_rows))
        f.write(";\n\n")

    return rows_written


def get_tables_in_order(conn: sqlite3.Connection) -> list[str]:
    """按依赖关系排序：先基础表，后关联表"""
    # 手动指定顺序（被引用的表在前）
    ordered = [
        "teams",
        "users",
        "players",
        "player_season_stats",
        "scraped_player_data",
        "dongqiudi_teams",
        "dongqiudi_coaches",
        "dongqiudi_players",
        "dongqiudi_player_abilities",
        "dongqiudi_player_season_summaries",
        "dongqiudi_matches",
        "dongqiudi_standings",
        "zafronix_matches",
        "zafronix_standings",
        "zafronix_tournament",
        "bookmakers",
        "match_odds",
        "match_odds_history",
        "match_odds_summary",
        "recommendation_cache",
        "simulation_runs",
        "simulation_results",
        "knockout_brackets",
        "data_source_status",
        "data_refresh_logs",
    ]

    all_tables = set(get_table_names(conn))
    result = [t for t in ordered if t in all_tables]
    # 把不在列表里的表追加到最后
    for t in all_tables:
        if t not in result:
            result.append(t)
    return result


def main():
    if len(sys.argv) < 3:
        print("用法: python sqlite_to_mysql.py <sqlite_db_path> <output_sql_path>")
        sys.exit(1)

    sqlite_path = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.exists(sqlite_path):
        print(f"错误: SQLite 文件不存在: {sqlite_path}")
        sys.exit(1)

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row

    tables = get_tables_in_order(conn)

    print(f"共发现 {len(tables)} 张表，开始导出...\n")

    total_rows = 0
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("-- ==========================================\n")
        f.write("-- WorldCup SQLite → MySQL 数据迁移\n")
        f.write(f"-- 源数据库: {sqlite_path}\n")
        f.write("-- ==========================================\n\n")
        f.write("SET NAMES utf8mb4;\n")
        f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")

        for table in tables:
            print(f"  导出表: {table} ... ", end="", flush=True)
            count = export_table(conn, table, f)
            print(f"{count} 行")
            total_rows += count

        f.write("\nSET FOREIGN_KEY_CHECKS = 1;\n")
        f.write("-- ==========================================\n")
        f.write(f"-- 导出完成，共 {len(tables)} 张表，{total_rows} 行数据\n")
        f.write("-- ==========================================\n")

    conn.close()

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"\n✅ 导出完成!")
    print(f"   输出文件: {output_path}")
    print(f"   文件大小: {size_mb:.2f} MB")
    print(f"   表数量: {len(tables)}")
    print(f"   总数据行数: {total_rows}")
    print()
    print("导入到 MySQL 的命令:")
    print(f"  mysql -u 用户名 -p 数据库名 < {os.path.basename(output_path)}")


if __name__ == "__main__":
    main()
