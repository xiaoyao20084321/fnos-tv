from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# SQLite 文件数据库
engine = create_engine('sqlite:///data/data.db', echo=False)

# 线程安全的 Session
SessionLocal = scoped_session(sessionmaker(bind=engine))
