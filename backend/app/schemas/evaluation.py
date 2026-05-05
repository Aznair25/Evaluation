from pydantic import BaseModel
from datetime import datetime, date
from typing import Any
import uuid
from app.models.evaluation import EvaluationStatus


class EvaluateRequest(BaseModel):
    student_name: str | None = None
    evaluator_name: str | None = None
    institution: str | None = None
    date: date | None = None
    language: str = "fr"


class EvaluationStarted(BaseModel):
    evaluation_id: uuid.UUID
    status: str
    message: str


class EvaluationStatus_(BaseModel):
    evaluation_id: uuid.UUID
    status: EvaluationStatus
    progress_percentage: int
    current_step: str | None

    model_config = {"from_attributes": True}


class CriterionResult(BaseModel):
    achieved: bool | None = None
    evidence: list[str] = []
    comment_fr: str | None = None
    comment_en: str | None = None
    azure_scores: dict[str, float] | None = None
    error: str | None = None


class EvaluationResult(BaseModel):
    evaluation_id: uuid.UUID
    status: EvaluationStatus
    cefr_level: str | None
    sub_level_rule: str | None
    communicative_profile_fr: str | None
    communicative_profile_en: str | None
    criteria: dict[str, Any] | None
    global_comment_fr: str | None
    global_comment_en: str | None
    report_url: str | None
    transcript: str | None
    audio_duration_seconds: float | None
    student_speaking_duration_seconds: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluationListItem(BaseModel):
    evaluation_id: uuid.UUID
    status: EvaluationStatus
    cefr_level: str | None
    student_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
