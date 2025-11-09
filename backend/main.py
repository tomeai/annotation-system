import json
import os
from datetime import datetime
from typing import List, Dict

import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

from backend.conf import BASE_PATH
from backend.core.crud import save_file_info, get_file_info, save_data_records, get_data_records_from_db, \
    update_data_annotation, get_data_stats_from_db, get_all_files, delete_file_info, export_data_from_db
from backend.core.db import init_database
from backend.core.schema import DataUpdateRequest, ExportRequest, AnnotationRequest
from backend.core.service import allowed_file, read_jsonl_file

app = FastAPI(title="优质数据集筛选系统", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
UPLOAD_FOLDER = os.path.join(BASE_PATH, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_PATH, "output")
DIST_DIR = os.path.join(BASE_PATH.parent, "frontend/dist")

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 启动时初始化数据库
init_database()


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


@app.post("/api/export")
async def export_data(request: ExportRequest):
    """导出筛选后的数据"""
    # 获取文件信息
    file_info = get_file_info(request.filename)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 导出指定类型的数据（正确或错误）
    result = await export_data_from_db(file_info['id'], request.export_name, request.export_type)

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


# Mount static files AFTER all API routes
app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")


# 根路由返回 index.html (MUST be LAST to avoid catching API routes)
@app.get("/{full_path:path}")
async def serve_vue(full_path: str):
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"error": "index.html not found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
