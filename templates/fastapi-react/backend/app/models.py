import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProviderRun(Base):
    __tablename__ = "provider_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_name: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running / complete / error
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    raw_records: Mapped[list["RawRecord"]] = relationship(back_populates="run")


class RawRecord(Base):
    __tablename__ = "raw_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("provider_runs.id"))
    external_id: Mapped[str] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    run: Mapped["ProviderRun"] = relationship(back_populates="raw_records")


class NormalizedRecord(Base):
    __tablename__ = "normalized_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(256), unique=True)
    source: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(64))
    value: Mapped[float] = mapped_column(Float)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    raw_payload: Mapped[dict] = mapped_column(JSON)

    scores: Mapped[list["RecordScore"]] = relationship(back_populates="record", order_by="RecordScore.scored_at.desc()")
    action: Mapped["RecordAction | None"] = relationship(back_populates="record", uselist=False)
    action_events: Mapped[list["RecordActionEvent"]] = relationship(
        back_populates="record",
        order_by="RecordActionEvent.created_at.desc()",
    )
    notification_preview: Mapped["NotificationPreview | None"] = relationship(
        back_populates="record",
        uselist=False,
    )


class RecordScore(Base):
    __tablename__ = "record_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    normalized_record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("normalized_records.id"))
    fit: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(16))        # high / medium / low
    recommendation: Mapped[str] = mapped_column(String(16))  # accept / review / skip
    explanation: Mapped[dict] = mapped_column(JSON)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    record: Mapped["NormalizedRecord"] = relationship(back_populates="scores")


class RecordAction(Base):
    __tablename__ = "record_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    normalized_record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("normalized_records.id"), unique=True)
    action_type: Mapped[str] = mapped_column(String(16))   # accept / skip / save
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending / accepted / skipped / saved
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    record: Mapped["NormalizedRecord"] = relationship(back_populates="action")


class RecordActionEvent(Base):
    __tablename__ = "record_action_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    normalized_record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("normalized_records.id"))
    action_type: Mapped[str] = mapped_column(String(16))   # accept / skip / save
    status: Mapped[str] = mapped_column(String(16))        # accepted / skipped / saved
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    record: Mapped["NormalizedRecord"] = relationship(back_populates="action_events")


class NotificationPreview(Base):
    __tablename__ = "notification_previews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    normalized_record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("normalized_records.id"), unique=True)
    delivery_channel: Mapped[str] = mapped_column(String(32), default="preview")
    delivery_status: Mapped[str] = mapped_column(String(32), default="previewed")
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    record: Mapped["NormalizedRecord"] = relationship(back_populates="notification_preview")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(256), default="Agent conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation",
        order_by="ConversationMessage.created_at",
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(16))  # user / assistant / tool
    content: Mapped[str] = mapped_column(String(4096))
    message_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
