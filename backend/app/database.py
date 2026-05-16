from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

#Creating database engine
engine = create_engine(settings.DATABASE_URL)

#Create session factory (each api request gets its own session)
SessionLocal = sessionmaker(autocommit = False, autoflush=False,bind = engine)

#Every class will inherit from this
class Base(DeclarativeBase):
    pass

def get_db():
    '''Dependency : give each API request a database session, auto close it after'''
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

