import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

from backend.conf import BASE_PATH

DATABASE_FILE = os.path.join(BASE_PATH, "files.db")


def save_file_info(filename: str, original_filename: str, file_size: int, total_records: int,
                   annotation_type: str = "qa"):
    """保存文件信息到数据库"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO files 
        (filename, original_filename, file_size, total_records, annotation_type, last_modified)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (filename, original_filename, file_size, total_records, annotation_type))

    conn.commit()
    conn.close()


def get_file_info(filename: str) -> Optional[Dict]:
    """获取指定文件的信息"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('''
                   SELECT id,
                          filename,
                          original_filename,
                          file_size,
                          total_records,
                          annotation_type,
                          upload_time,
                          last_modified,
                          status
                   FROM files
                   WHERE filename = ?
                   ''', (filename,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'id': row[0],
            'filename': row[1],
            'original_filename': row[2],
            'file_size': row[3],
            'total_records': row[4],
            'annotation_type': row[5],
            'upload_time': row[6],
            'last_modified': row[7],
            'status': row[8]
        }
    return None


def get_all_files() -> List[Dict]:
    """获取所有文件信息"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('''
                   SELECT id,
                          filename,
                          original_filename,
                          file_size,
                          total_records,
                          annotation_type,
                          upload_time,
                          last_modified,
                          status
                   FROM files
                   WHERE status = 'active'
                   ORDER BY upload_time DESC
                   ''')

    rows = cursor.fetchall()
    conn.close()

    files = []
    for row in rows:
        files.append({
            'id': row[0],
            'filename': row[1],
            'original_filename': row[2],
            'file_size': row[3],
            'total_records': row[4],
            'annotation_type': row[5],
            'upload_time': row[6],
            'last_modified': row[7],
            'status': row[8]
        })

    return files


def delete_file_info(filename: str):
    """删除文件信息（软删除）"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # 获取文件ID
    cursor.execute('SELECT id FROM files WHERE filename = ?', (filename,))
    file_row = cursor.fetchone()

    if file_row:
        file_id = file_row[0]
        # 软删除文件记录
        cursor.execute('UPDATE files SET status = ? WHERE filename = ?', ('deleted', filename))
        # 软删除相关的数据记录
        cursor.execute('UPDATE data_records SET status = ? WHERE file_id = ?', ('deleted', file_id))

    conn.commit()
    conn.close()


def save_data_records(file_id: int, data_records: List[Dict]):
    """保存数据记录到数据库"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    for record in data_records:
        # 生成唯一ID
        unique_id = f"{file_id}_{record['line_number']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        cursor.execute('''
            INSERT OR REPLACE INTO data_records 
            (file_id, unique_id, line_number, system, query, response, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (
            file_id,
            unique_id,
            record['line_number'],
            record.get('system', ''),
            record.get('query', ''),
            record.get('response', '')
        ))

    conn.commit()
    conn.close()


def get_data_records_from_db(file_id: int, search: str = "", annotation_status: str = "all",
                             selected_only: bool = False, page: int = 1, per_page: int = 20) -> Dict:
    """从数据库获取数据记录"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # 构建查询条件
    where_conditions = ["file_id = ?", "status = 'active'"]
    params = [file_id]

    if search:
        where_conditions.append("(LOWER(system) LIKE ? OR LOWER(query) LIKE ? OR LOWER(response) LIKE ?)")
        search_param = f"%{search.lower()}%"
        params.extend([search_param, search_param, search_param])

    if annotation_status == "annotated":
        where_conditions.append("annotation_result IS NOT NULL")
    elif annotation_status == "not_annotated":
        where_conditions.append("annotation_result IS NULL")

    # 获取总数
    count_query = f"SELECT COUNT(*) FROM data_records WHERE {' AND '.join(where_conditions)}"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]

    # 分页查询
    offset = (page - 1) * per_page
    query = f'''
        SELECT id, unique_id, line_number, system, query, response, annotation_result, 
               created_at, updated_at
        FROM data_records 
        WHERE {' AND '.join(where_conditions)}
        ORDER BY line_number
        LIMIT ? OFFSET ?
    '''
    params.extend([per_page, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # 格式化数据
    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'unique_id': row[1],
            'line_number': row[2],
            'system': row[3],
            'query': row[4],
            'response': row[5],
            'annotation_result': row[6],
            'created_at': row[7],
            'updated_at': row[8],
            'selected': False
        })

    return {
        "data": data,
        "total_count": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": (total_count + per_page - 1) // per_page
    }


def update_data_annotation(unique_id: str, annotation_result: str) -> bool:
    """更新数据记录的标注结果"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('''
                   UPDATE data_records
                   SET annotation_result = ?,
                       updated_at        = CURRENT_TIMESTAMP
                   WHERE unique_id = ?
                     AND status = 'active'
                   ''', (annotation_result, unique_id))

    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()

    return affected_rows > 0


def get_data_stats_from_db(file_id: int) -> Dict:
    """从数据库获取数据统计信息"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # 获取文件信息以确定标注类型
    cursor.execute('SELECT annotation_type FROM files WHERE id = ?', (file_id,))
    file_row = cursor.fetchone()
    annotation_type = file_row[0] if file_row else 'qa'

    # 获取总记录数
    cursor.execute('''
                   SELECT COUNT(*)
                   FROM data_records
                   WHERE file_id = ?
                     AND status = 'active'
                   ''', (file_id,))
    total_count = cursor.fetchone()[0]

    if annotation_type == 'scoring':
        # 对于评分标注，按评分值统计
        # 评分 >= 4 为优质（correct），< 4 为劣质（incorrect）
        cursor.execute('''
                       SELECT annotation_result
                       FROM data_records
                       WHERE file_id = ?
                         AND status = 'active'
                         AND annotation_result IS NOT NULL
                       ''', (file_id,))

        results = cursor.fetchall()
        correct_count = 0  # 优质（评分>=4）
        incorrect_count = 0  # 劣质（评分<4）

        for (result,) in results:
            try:
                score = float(result)
                if score >= 4:
                    correct_count += 1
                else:
                    incorrect_count += 1
            except (ValueError, TypeError):
                pass

        unannotated_count = total_count - correct_count - incorrect_count
    else:
        # 对于QA标注，按原来的方式统计
        cursor.execute('''
                       SELECT annotation_result, COUNT(*)
                       FROM data_records
                       WHERE file_id = ?
                         AND status = 'active'
                       GROUP BY annotation_result
                       ''', (file_id,))

        annotation_stats = dict(cursor.fetchall())

        correct_count = annotation_stats.get('correct', 0)
        incorrect_count = annotation_stats.get('incorrect', 0)
        unannotated_count = total_count - correct_count - incorrect_count

    conn.close()

    return {
        "total_count": total_count,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "unannotated_count": unannotated_count,
        "annotation_distribution": {
            "correct": correct_count,
            "incorrect": incorrect_count,
            "unannotated": unannotated_count
        }
    }


def export_data_from_db(file_id: int, export_name: str, export_type: str = "correct") -> Dict:
    """从数据库导出标注数据（正确或错误）"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # 验证导出类型
    if export_type not in ["correct", "incorrect"]:
        raise ValueError("export_type 必须是 'correct' 或 'incorrect'")

    # 根据类型查询数据
    cursor.execute('''
                   SELECT system, query, response
                   FROM data_records
                   WHERE file_id = ?
                     AND annotation_result = ?
                     AND status = 'active'
                   ORDER BY line_number
                   ''', (file_id, export_type))

    rows = cursor.fetchall()
    conn.close()

    # 准备导出数据
    export_data = []
    for row in rows:
        export_data.append({
            'system': row[0] or '',
            'query': row[1] or '',
            'response': row[2] or ''
        })

    # 创建导出文件
    export_path = os.path.join(OUTPUT_FOLDER, export_name)

    try:
        async def write_export_data():
            async with aiofiles.open(export_path, 'w', encoding='utf-8') as f:
                for item in export_data:
                    await f.write(json.dumps(item, ensure_ascii=False) + '\n')
            return True

        # 运行异步函数
        import asyncio
        success = asyncio.run(write_export_data())

        if success:
            return {
                "export_path": export_path,
                "export_count": len(export_data)
            }
        else:
            return None
    except Exception as e:
        print(f"Error exporting data: {e}")
        return None
