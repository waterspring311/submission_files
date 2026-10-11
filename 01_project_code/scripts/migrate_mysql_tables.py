
"""
为MySQL表添加缺失的字段
"""
import sys
from pathlib import Path

import pymysql

PROJECT_CODE_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_CODE_DIR))

from app.config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("="*70)
print("开始修复MySQL表结构")
print("="*70)

# 1. 修复 resume_record 表
print("\n1. 修复 resume_record 表:")
try:
    cursor.execute("ALTER TABLE resume_record ADD COLUMN resume_text TEXT")
    print("OK: 添加 resume_text 成功")
except Exception as e:
    if "Duplicate column name" in str(e):
        print("INFO: resume_text 字段已存在")
    else:
        print(f"WARN: 添加 resume_text 失败: {e}")

try:
    cursor.execute("ALTER TABLE resume_record ADD COLUMN skills TEXT")
    print("OK: 添加 skills 成功")
except Exception as e:
    if "Duplicate column name" in str(e):
        print("INFO: skills 字段已存在")
    else:
        print(f"WARN: 添加 skills 失败: {e}")

# 2. 修复 talent_pool 表
print("\n2. 修复 talent_pool 表:")
try:
    cursor.execute("ALTER TABLE talent_pool ADD COLUMN resume_file_path VARCHAR(500)")
    print("OK: 添加 resume_file_path 成功")
except Exception as e:
    if "Duplicate column name" in str(e):
        print("INFO: resume_file_path 字段已存在")
    else:
        print(f"WARN: 添加 resume_file_path 失败: {e}")

# 3. 修复管理员审核字段
print("\n3. 修复管理员审核字段:")
for table_name in ("job_positions", "resume_record"):
    for column_name, ddl in (
        ("review_status", f"ALTER TABLE {table_name} ADD COLUMN review_status VARCHAR(50) DEFAULT 'pending'"),
        ("review_notes", f"ALTER TABLE {table_name} ADD COLUMN review_notes TEXT"),
        ("reviewed_at", f"ALTER TABLE {table_name} ADD COLUMN reviewed_at DATETIME"),
    ):
        try:
            cursor.execute(ddl)
            print(f"OK: {table_name}.{column_name} 添加成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print(f"INFO: {table_name}.{column_name} 字段已存在")
            else:
                print(f"WARN: 添加 {table_name}.{column_name} 失败: {e}")

try:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            config_key VARCHAR(100) NOT NULL UNIQUE,
            config_value TEXT,
            config_group VARCHAR(50) NOT NULL,
            label VARCHAR(100) NOT NULL,
            is_secret INT DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )
    print("OK: system_config 表已创建或已存在")
except Exception as e:
    print(f"WARN: 创建 system_config 表失败: {e}")

conn.commit()
cursor.close()
conn.close()

print("\n" + "="*70)
print("OK: MySQL表结构修复完成！")
print("="*70)
