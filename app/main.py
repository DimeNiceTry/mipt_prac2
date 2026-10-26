import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, StringConstraints
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

metadata = MetaData()
notes = Table(
    "notes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("text", String(1000), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


def database_engine():
    if os.environ.get("DB_HOST"):
        url = URL.create(
            "postgresql+psycopg",
            username=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT", "5432")),
            database=os.environ["DB_NAME"],
        )
        return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
    return create_engine(
        "sqlite:////tmp/notes.db",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )


@asynccontextmanager
async def lifespan(application: FastAPI):
    engine = database_engine()
    try:
        metadata.create_all(engine)
        application.state.engine = engine
        yield
    finally:
        engine.dispose()


app = FastAPI(title=os.environ.get("APP_NAME", "Lab 2: Notes"), lifespan=lifespan)


class NoteInput(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class Note(NoteInput):
    id: int
    created_at: datetime


@app.get("/")
def index():
    return {"application": app.title, "health": "/health", "docs": "/docs"}


@app.get("/health")
def health(request: Request):
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok"}


@app.get("/notes", response_model=list[Note])
def list_notes(request: Request):
    with request.app.state.engine.connect() as connection:
        return list(connection.execute(select(notes).order_by(notes.c.id)).mappings())


@app.post("/notes", response_model=Note, status_code=status.HTTP_201_CREATED)
def create_note(note: NoteInput, request: Request):
    with request.app.state.engine.begin() as connection:
        return connection.execute(
            notes.insert().values(text=note.text).returning(notes)
        ).mappings().one()
