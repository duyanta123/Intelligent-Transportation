"""SQLAlchemy 引擎与会话管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.db_url, pool_pre_ping=True, pool_recycle=3600, pool_size=8, max_overflow=16)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """全部 ORM 模型的基类"""
