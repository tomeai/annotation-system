import json
import os
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any

import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="优质数据集筛选系统", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
DATABASE_FILE = "files.db"
ALLOWED_EXTENSIONS = {"jsonl"}

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def init_database():
    """初始化SQLite数据库"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # 创建文件信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            original_filename TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            total_records INTEGER NOT NULL,
            annotation_type TEXT DEFAULT 'qa',
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
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
        CREATE TABLE IF NOT EXISTS data_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            unique_id TEXT NOT NULL UNIQUE,
            line_number INTEGER NOT NULL,
            system TEXT,
            query TEXT,
            response TEXT,
            annotation_result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (file_id) REFERENCES files (id)
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


def save_file_info(filename: str, original_filename: str, file_size: int, total_records: int, annotation_type: str = "qa"):
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
        SELECT id, filename, original_filename, file_size, total_records, 
               annotation_type, upload_time, last_modified, status
        FROM files WHERE filename = ?
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
        SELECT id, filename, original_filename, file_size, total_records, 
               annotation_type, upload_time, last_modified, status
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
        SET annotation_result = ?, updated_at = CURRENT_TIMESTAMP
        WHERE unique_id = ? AND status = 'active'
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
        SELECT COUNT(*) FROM data_records 
        WHERE file_id = ? AND status = 'active'
    ''', (file_id,))
    total_count = cursor.fetchone()[0]
    
    if annotation_type == 'scoring':
        # 对于评分标注，按评分值统计
        # 评分 >= 4 为优质（correct），< 4 为劣质（incorrect）
        cursor.execute('''
            SELECT annotation_result FROM data_records 
            WHERE file_id = ? AND status = 'active' AND annotation_result IS NOT NULL
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
            WHERE file_id = ? AND status = 'active'
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


# 启动时初始化数据库
init_database()


class DataUpdateRequest(BaseModel):
    filename: str
    line_number: int
    updates: Dict[str, Any]


class AnnotationRequest(BaseModel):
    unique_id: str
    annotation_result: str


class ExportRequest(BaseModel):
    filename: str
    export_name: Optional[str] = "filtered_dataset.jsonl"
    selected_only: Optional[bool] = True
    export_type: Optional[str] = "correct"  # "correct" 或 "incorrect"


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


async def read_jsonl_file(file_path: str) -> List[Dict]:
    """读取JSONL文件并返回数据列表"""
    data = []
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            line_num = 1
            async for line in f:
                line = line.strip()
                if line:
                    try:
                        data_item = json.loads(line)
                        # 添加元数据
                        data_item['line_number'] = line_num
                        data_item['selected'] = False
                        data_item['annotation_result'] = None
                        data.append(data_item)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing line {line_num}: {e}")
                        continue
                line_num += 1
    except Exception as e:
        print(f"Error reading file: {e}")
    return data


async def write_jsonl_file(data: List[Dict], file_path: str) -> bool:
    """将数据写入JSONL文件"""
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            for item in data:
                # 移除元数据字段
                clean_item = {k: v for k, v in item.items()
                              if k not in ['line_number', 'selected', 'quality_score']}
                await f.write(json.dumps(clean_item, ensure_ascii=False) + '\n')
        return True
    except Exception as e:
        print(f"Error writing file: {e}")
        return False


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), annotation_type: str = Form("qa")):
    """上传JSONL文件"""
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="不支持的文件格式")

    # 验证标注类型
    if annotation_type not in ["qa", "scoring"]:
        raise HTTPException(status_code=400, detail="不支持的标注类型")

    # 生成唯一文件名（避免重名）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    # 保存文件
    content = await file.read()
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    # 读取文件数据
    data = await read_jsonl_file(file_path)

    # 保存文件信息到数据库
    save_file_info(filename, file.filename, len(content), len(data), annotation_type)
    
    # 获取文件ID
    file_info = get_file_info(filename)
    if file_info:
        # 将数据记录保存到数据库
        save_data_records(file_info['id'], data)

    return {
        "message": "文件上传成功",
        "filename": filename,
        "original_filename": file.filename,
        "file_size": len(content),
        "total_count": len(data),
        "annotation_type": annotation_type,
        "data": data
    }


@app.get("/api/data")
async def get_data(
        filename: str = Query(...),
        search: str = Query("", description="搜索关键词"),
        annotation_status: str = Query("all", description="标注状态: all/annotated/not_annotated"),
        selected_only: bool = Query(False, description="仅显示已选择"),
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取数据（支持筛选和分页）"""
    # 获取文件信息
    file_info = get_file_info(filename)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 从数据库获取数据记录
    result = get_data_records_from_db(
        file_id=file_info['id'],
        search=search,
        annotation_status=annotation_status,
        selected_only=selected_only,
        page=page,
        per_page=per_page
    )

    return result


@app.post("/api/update")
async def update_data(request: DataUpdateRequest):
    """更新数据项"""
    file_path = os.path.join(UPLOAD_FOLDER, request.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    # 读取所有数据
    all_data = await read_jsonl_file(file_path)

    # 更新指定行
    for item in all_data:
        if item.get('line_number') == request.line_number:
            item.update(request.updates)
            break
    else:
        raise HTTPException(status_code=404, detail="找不到指定的数据项")

    # 写回文件
    if await write_jsonl_file(all_data, file_path):
        return {"message": "更新成功"}
    else:
        raise HTTPException(status_code=500, detail="更新失败")


@app.post("/api/annotate")
async def annotate_data(request: AnnotationRequest):
    """标注数据"""
    success = update_data_annotation(request.unique_id, request.annotation_result)
    
    if success:
        return {"message": "标注成功"}
    else:
        raise HTTPException(status_code=404, detail="找不到指定的数据项")


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
        WHERE file_id = ? AND annotation_result = ? AND status = 'active'
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


@app.post("/api/export")
async def export_data(request: ExportRequest):
    """导出筛选后的数据"""
    # 获取文件信息
    file_info = get_file_info(request.filename)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 导出指定类型的数据（正确或错误）
    result = export_data_from_db(file_info['id'], request.export_name, request.export_type)
    
    if result:
        export_type_text = "正确" if request.export_type == "correct" else "错误"
        return {
            "message": "导出成功",
            "export_path": result["export_path"],
            "export_count": result["export_count"],
            "export_type": export_type_text
        }
    else:
        raise HTTPException(status_code=500, detail="导出失败")


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """下载文件"""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(file_path, media_type='application/octet-stream', filename=filename)


@app.get("/api/stats/{filename}")
async def get_stats(filename: str):
    """获取数据统计信息"""
    # 获取文件信息
    file_info = get_file_info(filename)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 从数据库获取统计信息
    stats = get_data_stats_from_db(file_info['id'])
    
    return stats


@app.get("/api/files")
async def get_files():
    """获取所有文件列表"""
    try:
        files = get_all_files()
        
        # 格式化文件大小
        for file in files:
            file_size = file['file_size']
            if file_size < 1024:
                file['file_size_formatted'] = f"{file_size} B"
            elif file_size < 1024 * 1024:
                file['file_size_formatted'] = f"{file_size / 1024:.1f} KB"
            else:
                file['file_size_formatted'] = f"{file_size / (1024 * 1024):.1f} MB"
        
        return {
            "message": "获取文件列表成功",
            "files": files,
            "total_count": len(files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@app.get("/api/file/{filename}")
async def get_file_info_api(filename: str):
    """获取指定文件的详细信息"""
    try:
        file_info = get_file_info(filename)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 格式化文件大小
        file_size = file_info['file_size']
        if file_size < 1024:
            file_info['file_size_formatted'] = f"{file_size} B"
        elif file_size < 1024 * 1024:
            file_info['file_size_formatted'] = f"{file_size / 1024:.1f} KB"
        else:
            file_info['file_size_formatted'] = f"{file_size / (1024 * 1024):.1f} MB"
        
        return {
            "message": "获取文件信息成功",
            "file_info": file_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")


@app.delete("/api/file/{filename}")
async def delete_file(filename: str):
    """删除文件"""
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 删除物理文件
        os.remove(file_path)
        
        # 删除数据库记录（软删除）
        delete_file_info(filename)
        
        return {"message": "文件删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@app.get("/")
async def root():
    return {"message": "优质数据集筛选系统 API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
