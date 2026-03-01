import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .database import Base

class DebateRecord(Base):
    __tablename__ = "debates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic = Column(String, nullable=False)
    persona = Column(String, nullable=False, default="default")
    user_side = Column(String, nullable=False, default="auto") # 'pro', 'con', or 'auto'
    pro_claims = Column(JSONB, nullable=False, default=list)
    con_claims = Column(JSONB, nullable=False, default=list)
    max_rounds = Column(Integer, nullable=False, default=6)
    status = Column(String, nullable=False, default="running")  # running, waiting_on_user, completed
    belief = Column(Float, nullable=False, default=0.5)
    winner = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rounds = relationship("RoundRecordModel", back_populates="debate", cascade="all, delete-orphan", order_by="RoundRecordModel.round_number")

class RoundRecordModel(Base):
    __tablename__ = "rounds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    debate_id = Column(UUID(as_uuid=True), ForeignKey("debates.id"), nullable=False)
    
    round_number = Column(Integer, nullable=False)
    side = Column(String, nullable=False) # 'pro' or 'con'
    
    claim = Column(String, nullable=False)
    premises = Column(JSONB, nullable=False)
    inference = Column(String, nullable=False)
    strength = Column(Float, nullable=False, default=0.0)
    reasoning_type = Column(String, nullable=False, default="causal")
    
    belief_after = Column(Float, nullable=False)
    is_user_move = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    debate = relationship("DebateRecord", back_populates="rounds")
