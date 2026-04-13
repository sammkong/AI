from pydantic import BaseModel
from typing import Optional


class TrainingJobRequest(BaseModel):
    job_id: str
    job_type: str
    task_type: str
    dataset_version: str
    requested_by: str
    created_at: str


class TrainingMetrics(BaseModel):
    intent_f1: Optional[float] = None
    domain_accuracy: Optional[float] = None


class TrainingJobResult(BaseModel):
    job_id: str
    status: str
    model_version: Optional[str] = None
    finished_at: str
    metrics: TrainingMetrics
    error_message: Optional[str] = None
