from sqlalchemy.ext.declarative import declarative_base

# 创建 ORM 基类
Base = declarative_base()

# 导入所有模型，确保 Alembic 能够检测到它们
from .recordDb import RecordDb
from .videoConfigDb import videoConfigList, videoConfigUrl

