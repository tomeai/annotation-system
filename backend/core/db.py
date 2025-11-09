import os
import sqlite3

from backend.conf import BASE_PATH

DATABASE_FILE = os.path.join(BASE_PATH, "files.db")


def init_database():
    """初始化SQLite数据库"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # 创建文件信息表
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS files
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       filename
                       TEXT
                       NOT
                       NULL
                       UNIQUE,
                       original_filename
                       TEXT
                       NOT
                       NULL,
                       file_size
                       INTEGER
                       NOT
                       NULL,
                       total_records
                       INTEGER
                       NOT
                       NULL,
                       annotation_type
                       TEXT
                       DEFAULT
                       'qa',
                       upload_time
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       last_modified
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       status
                       TEXT
                       DEFAULT
                       'active'
                   )
                   ''')

    # 检查并添加 annotation_type 列（如果不存在）
    try:
        cursor.execute("SELECT annotation_type FROM files LIMIT 1")
    except sqlite3.OperationalError:
        # 列不存在，添加它
        cursor.execute("ALTER TABLE files ADD COLUMN annotation_type TEXT DEFAULT 'qa'")
        # 更新所有现有记录的 annotation_type 为默认值 'qa'
        cursor.execute("UPDATE files SET annotation_type = 'qa' WHERE annotation_type IS NULL")
        conn.commit()

    # 创建数据记录表
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS data_records
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       file_id
                       INTEGER
                       NOT
                       NULL,
                       unique_id
                       TEXT
                       NOT
                       NULL
                       UNIQUE,
                       line_number
                       INTEGER
                       NOT
                       NULL,
                       system
                       TEXT,
                       query
                       TEXT,
                       response
                       TEXT,
                       annotation_result
                       TEXT,
                       created_at
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       updated_at
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       status
                       TEXT
                       DEFAULT
                       'active',
                       FOREIGN
                       KEY
                   (
                       file_id
                   ) REFERENCES files
                   (
                       id
                   )
                       )
                   ''')

    # 创建索引
    cursor.execute('''
                   CREATE INDEX IF NOT EXISTS idx_data_records_file_id
                       ON data_records (file_id)
                   ''')

    cursor.execute('''
                   CREATE INDEX IF NOT EXISTS idx_data_records_unique_id
                       ON data_records (unique_id)
                   ''')

    cursor.execute('''
                   CREATE INDEX IF NOT EXISTS idx_data_records_annotation_result
                       ON data_records (annotation_result)
                   ''')

    conn.commit()
    conn.close()
