from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import sessionmaker, DeclarativeBase


DATABASE_URL = "sqlite:///ecommerce.db"

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Строка подключения для PostgreSQl
DATABASE_URL = "postgresql+asyncpg://ecommerce_user:xxxxxxxx@localhost:5432/ecommerce_db"

# Создаём Engine
async_engine = create_async_engine(DATABASE_URL, echo=True)


# Настраиваем фабрику сеансов
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)