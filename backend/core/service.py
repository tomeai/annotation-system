import json
from typing import List, Dict

import aiofiles

ALLOWED_EXTENSIONS = {"jsonl"}


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
