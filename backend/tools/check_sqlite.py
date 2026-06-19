"""查看 SQLite 数据库表结构和数据量"""
import sqlite3
import os

db_path = r"d:\code_space\WorldCup\backend\worldcup.db"

if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 获取所有表
cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table' "
    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
)
tables = [row[0] for row in cursor.fetchall()]

print(f"数据库文件: {db_path}")
print(f"文件大小: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")
print(f"共 {len(tables)} 张表:\n")
print(f"{'表名':<35} {'行数':>8}")
print("-" * 45)

total = 0
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
    count = cursor.fetchone()[0]
    total += count
    print(f"{table:<35} {count:>8}")

print("-" * 45)
print(f"{'总计':<35} {total:>8}")

conn.close()
