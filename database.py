from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# tell sqlalchemy to use sqlite database (where to connect)
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./lokerin.db"

 # Our connection to the database
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} # sqlite only allow one thread at a time, but we disable that restriction
)

# create a session factory // session is transaction with the database, each request gets its own session
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
) 

class Base(DeclarativeBase):
    pass

# Dependency Generator
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


