import asyncio
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.evaluation import Evaluation, EvaluationStatus
from app.schemas.evaluation import (
    EvaluateRequest,
    EvaluationStarted,
    EvaluationStatus_,
    EvaluationResult,
    EvaluationListItem,
)
from app.core.auth import get_current_user
from app.services.storage import StorageService
from app.workers.evaluation_pipeline import run_evaluation_pipeline

settings = get_settings()
router = APIRouter()

ALLOWED_AUDIO_TYPES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/ogg", "audio/flac", "audio/x-flac", "audio/mp4",
    "audio/m4a", "audio/x-m4a", "video/webm", "audio/webm",
}
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".webm"}


def _check_audio_file(file: UploadFile):
    import os
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file extension: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )


@router.post("/evaluate", response_model=EvaluationStarted, status_code=202)
async def start_evaluation(
    audio_file: UploadFile = File(...),
    student_name: str | None = Form(None),
    evaluator_name: str | None = Form(None),
    institution: str | None = Form(None),
    date: str | None = Form(None),
    language: str = Form("fr"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_audio_file(audio_file)

    # Check file size
    audio_bytes = await audio_file.read()
    max_bytes = settings.max_audio_size_mb * 1024 * 1024
    if len(audio_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_audio_size_mb}MB",
        )

    evaluation_id = uuid.uuid4()

    import os
    ext = os.path.splitext(audio_file.filename or "file.wav")[1].lower() or ".wav"
    audio_s3_key = f"audio/{evaluation_id}/original{ext}"

    # Upload audio to S3
    storage = StorageService()
    await asyncio.get_event_loop().run_in_executor(
        None, storage.upload_bytes, audio_bytes, audio_s3_key, audio_file.content_type or "audio/wav"
    )

    # Parse date
    eval_date = None
    if date:
        from datetime import date as date_type
        try:
            eval_date = date_type.fromisoformat(date)
        except ValueError:
            pass

    # Create DB record
    evaluation = Evaluation(
        id=evaluation_id,
        user_id=current_user.id,
        status=EvaluationStatus.PENDING,
        audio_s3_key=audio_s3_key,
        student_name=student_name,
        evaluator_name=evaluator_name,
        institution=institution,
        evaluation_date=eval_date,
        current_step="Queued for processing",
    )
    db.add(evaluation)
    await db.commit()

    # Start background processing
    asyncio.create_task(
        run_evaluation_pipeline(str(evaluation_id), audio_bytes, ext, language)
    )

    return EvaluationStarted(
        evaluation_id=evaluation_id,
        status="processing",
        message="Evaluation started. Use evaluation_id to track progress.",
    )


@router.get("/evaluations", response_model=list[EvaluationListItem])
async def list_evaluations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Evaluation)
        .where(Evaluation.user_id == current_user.id)
        .order_by(Evaluation.created_at.desc())
    )
    evaluations = result.scalars().all()
    return [
        EvaluationListItem(
            evaluation_id=e.id,
            status=e.status,
            cefr_level=e.cefr_level,
            student_name=e.student_name,
            created_at=e.created_at,
        )
        for e in evaluations
    ]


@router.get("/evaluations/{evaluation_id}/status", response_model=EvaluationStatus_)
async def get_evaluation_status(
    evaluation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    evaluation = await _get_evaluation_or_404(evaluation_id, current_user.id, db)
    return EvaluationStatus_(
        evaluation_id=evaluation.id,
        status=evaluation.status,
        progress_percentage=evaluation.progress_percentage,
        current_step=evaluation.current_step,
    )


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationResult)
async def get_evaluation(
    evaluation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    evaluation = await _get_evaluation_or_404(evaluation_id, current_user.id, db)

    report_url = None
    transcript = None

    storage = StorageService()
    if evaluation.report_s3_key:
        report_url = storage.generate_presigned_url(evaluation.report_s3_key)

    if evaluation.transcript_s3_key:
        try:
            transcript_bytes = await asyncio.get_event_loop().run_in_executor(
                None, storage.download_bytes, evaluation.transcript_s3_key
            )
            transcript_data = json.loads(transcript_bytes)
            transcript = transcript_data.get("full_text", "")
        except Exception:
            transcript = None

    return EvaluationResult(
        evaluation_id=evaluation.id,
        status=evaluation.status,
        cefr_level=evaluation.cefr_level,
        sub_level_rule=evaluation.sub_level_rule,
        communicative_profile_fr=evaluation.communicative_profile_fr,
        communicative_profile_en=evaluation.communicative_profile_en,
        criteria=evaluation.criteria_results,
        global_comment_fr=evaluation.global_comment_fr,
        global_comment_en=evaluation.global_comment_en,
        report_url=report_url,
        transcript=transcript,
        audio_duration_seconds=evaluation.audio_duration_seconds,
        student_speaking_duration_seconds=evaluation.student_speaking_duration_seconds,
        created_at=evaluation.created_at,
    )


@router.get("/evaluations/{evaluation_id}/events")
async def evaluation_events(
    evaluation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_evaluation_or_404(evaluation_id, current_user.id, db)

    async def event_generator() -> AsyncGenerator[str, None]:
        terminal_statuses = {EvaluationStatus.COMPLETED, EvaluationStatus.FAILED}
        while True:
            async with db.begin():
                result = await db.execute(
                    select(Evaluation).where(Evaluation.id == evaluation_id)
                )
                evaluation = result.scalar_one_or_none()

            if evaluation is None:
                break

            event_data = {
                "status": evaluation.status.value,
                "progress_percentage": evaluation.progress_percentage,
                "current_step": evaluation.current_step,
            }
            if evaluation.status == EvaluationStatus.COMPLETED:
                event_data["cefr_level"] = evaluation.cefr_level

            yield f"data: {json.dumps(event_data)}\n\n"

            if evaluation.status in terminal_statuses:
                break

            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/evaluations/{evaluation_id}/report")
async def download_report(
    evaluation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    evaluation = await _get_evaluation_or_404(evaluation_id, current_user.id, db)
    if not evaluation.report_s3_key:
        raise HTTPException(status_code=404, detail="Report not yet available")

    storage = StorageService()
    url = storage.generate_presigned_url(evaluation.report_s3_key, expiration=3600)
    return RedirectResponse(url=url)


async def _get_evaluation_or_404(
    evaluation_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Evaluation:
    result = await db.execute(
        select(Evaluation).where(Evaluation.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if evaluation.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return evaluation
