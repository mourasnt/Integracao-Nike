from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from app.db import Base

class Prefat(Base):
    __tablename__ = "prefats"
    id = Column(Integer, primary_key=True, index=True)
    prefat_base64 = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())