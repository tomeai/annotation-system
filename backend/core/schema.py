from typing import Dict, Any, Optional

from pydantic import BaseModel


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
