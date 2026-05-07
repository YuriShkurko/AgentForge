from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import NormalizedRecord, RecordScore
from app.schemas import (
    ActionOut,
    ExplanationOut,
    RecordOut,
    RecordsListOut,
    ScoreDetailOut,
    ScoredRecordOut,
    ScoredRecordsListOut,
    ScoreOut,
)
from app.services.score import run_score

router = APIRouter(prefix="/records", tags=["records"])


@router.get("", response_model=RecordsListOut)
async def list_records(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NormalizedRecord).order_by(NormalizedRecord.ingested_at.desc()).limit(limit)
    )
    records = result.scalars().all()
    return {"records": records}


@router.post("/score", response_model=ScoreOut)
async def score_records(
    rescore: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    result = await run_score(db, rescore=rescore)
    return result


@router.get("/scored", response_model=ScoredRecordsListOut)
async def list_scored_records(
    limit: int = Query(50, ge=1, le=200),
    undecided: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(NormalizedRecord)
        .options(
            selectinload(NormalizedRecord.scores),
            selectinload(NormalizedRecord.action),
        )
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    out = []
    for record in records:
        if not record.scores:
            continue
        latest_score = record.scores[0]

        if undecided and record.action is not None:
            continue

        out.append(
            ScoredRecordOut(
                record=RecordOut.model_validate(record),
                score=ScoreDetailOut(
                    fit=latest_score.fit,
                    label=latest_score.label,
                    recommendation=latest_score.recommendation,
                    explanation=ExplanationOut(**latest_score.explanation),
                ),
                action=ActionOut.model_validate(record.action) if record.action else None,
            )
        )

    out.sort(key=lambda r: r.score.fit, reverse=True)
    return {"records": out[:limit]}
