from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.providers.fixture.provider import FixtureRecordProvider
from app.schemas import IngestOut
from app.services.ingest import run_ingest

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("", response_model=IngestOut)
async def ingest(db: AsyncSession = Depends(get_db)):
    provider = FixtureRecordProvider()
    result = await run_ingest(provider, db)
    return result
