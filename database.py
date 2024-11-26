from sqlalchemy import Column, String, Integer, DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime
import os

# DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/img_vid_db"
DATABASE_URL = f"sqlite:///./img_vid_db.db"

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False}, echo=True)

class Base(DeclarativeBase): pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class MediaFile(Base):
    __tablename__ = "files"

    file_id = Column(String, primary_key=True, unique=True)
    path = Column(String, nullable=False)
    type = Column(String, nullable=False)  # IMG или VID
    size = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now())

Base.metadata.create_all(bind=engine)
