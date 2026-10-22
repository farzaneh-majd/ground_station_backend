from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Float, Integer, UniqueConstraint, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass

def now(): return datetime.now(timezone.utc)

class Satellite(Base):
    __tablename__ = 'satellites'
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

class Channel(Base):
    __tablename__ = 'telemetry_channels'
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    satellite_id: Mapped[str] = mapped_column(ForeignKey('satellites.id'), index=True)
    telemetry_id: Mapped[str] = mapped_column(String(80), index=True)
    subsystem: Mapped[str] = mapped_column(String(80), default='General')
    name: Mapped[str] = mapped_column(String(150))
    kind: Mapped[str] = mapped_column(String(20), default='struct')
    endian: Mapped[str] = mapped_column(String(12), default='big')
    source: Mapped[str] = mapped_column(String(20), default='UNKNOWN')
    fields: Mapped[list] = mapped_column(JSON, default=list)
    sample_rate_hz: Mapped[float | None] = mapped_column(Float, nullable=True)

class RawPacket(Base):
    __tablename__ = 'raw_packets'
    record_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    satellite_id: Mapped[str] = mapped_column(ForeignKey('satellites.id'), index=True)
    telemetry_id: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[str] = mapped_column(String(65535))
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    decoded: Mapped[dict] = mapped_column(JSON, default=dict)

class Command(Base):
    __tablename__ = 'commands'
    command_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    satellite_id: Mapped[str] = mapped_column(ForeignKey('satellites.id'), index=True)
    command_hex: Mapped[str] = mapped_column(String(4096))
    status: Mapped[str] = mapped_column(String(30), default='CREATED')
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    response: Mapped[dict] = mapped_column(JSON, default=dict)

class Summary(Base):
    __tablename__ = 'telemetry_summaries'
    __table_args__ = (UniqueConstraint('satellite_id','channel_id','field','window_start'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    satellite_id: Mapped[str] = mapped_column(ForeignKey('satellites.id'))
    channel_id: Mapped[str] = mapped_column(String(120))
    field: Mapped[str] = mapped_column(String(120))
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    count: Mapped[int] = mapped_column(Integer)
    mean: Mapped[float] = mapped_column(Float)
    minimum: Mapped[float] = mapped_column(Float)
    maximum: Mapped[float] = mapped_column(Float)
    stddev: Mapped[float] = mapped_column(Float)

class SyncCheckpoint(Base):
    __tablename__ = 'sync_checkpoints'
    satellite_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    through: Mapped[datetime] = mapped_column(DateTime(timezone=True))
