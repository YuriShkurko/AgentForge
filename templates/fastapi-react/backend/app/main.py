from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import actions, agent, ingest, notifications, records, runs, workspace


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Hybrid Scoring Demo", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(records.router)
app.include_router(runs.router)
app.include_router(actions.router)
app.include_router(actions.history_router)
app.include_router(notifications.router)
app.include_router(agent.router)
app.include_router(workspace.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
