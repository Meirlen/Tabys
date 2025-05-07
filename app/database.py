from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import get_settings

settings = get_settings()

SQLALCHEMY_DATABASE_URL = f'postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_DB_HOST}/{settings.POSTGRES_DB}'
# SQLALCHEMY_DATABASE_URL_DRIVER_LOCATION = f'postgresql://{settings.POSTGRES_USER_1}:{settings.POSTGRES_PASSWORD_1}@{settings.POSTGRES_DB_HOST_1}:{settings.POSTGRES_PORT_1}/{settings.POSTGRES_DB_1}'



engine = create_engine(SQLALCHEMY_DATABASE_URL,pool_size=40)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# engine1 = create_engine(SQLALCHEMY_DATABASE_URL_DRIVER_LOCATION,pool_size=40)
# SessionLocal_1 = sessionmaker(autocommit=False, autoflush=False, bind=engine1)

Base = declarative_base()



def get_db_singleton():
    db = SessionLocal()
    # print("Db start connectiion")
    try:
        return db
    finally:
        # print('Db session closed')
        db.close()

def get_db():
    db = SessionLocal()
    # print("Db start connectiion")
    # print(engine.pool.status())
    try:
        yield db
    finally:
        # print('Db session closed')
        db.close()        

# def get_db_1():
#     db = SessionLocal_1()
#     # print("Db start connectiion")
#     # print(engine.pool.status())
#     try:
#         yield db
#     finally:
#         # print('Db session closed')
#         db.close() 

