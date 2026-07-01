"""
数据库连接管理

提供异步数据库引擎、会话工厂和基类。

安全特性:
- 所有查询使用参数化（SQLAlchemy ORM 已保证）
- 禁止动态拼接 SQL
- 连接池大小限制（防止连接耗尽）
- 生产环境支持 SSL 连接
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# 连接池配置
POOL_SIZE = 20
MAX_OVERFLOW = 10
POOL_TIMEOUT = 30  # 获取连接的超时时间（秒）
POOL_RECYCLE = 3600  # 连接回收时间（秒）

# 检测是否使用 SQLite
db_url = str(settings.DATABASE_URL)
is_sqlite = "sqlite" in db_url.lower()

# 构建引擎参数
if is_sqlite:
    # SQLite 不支持连接池参数
    engine_kwargs = {
        "echo": False,
        "connect_args": {"check_same_thread": False},
    }
else:
    # PostgreSQL 连接池配置
    engine_kwargs = {
        "echo": False,
        "pool_size": POOL_SIZE,
        "max_overflow": MAX_OVERFLOW,
        "pool_timeout": POOL_TIMEOUT,
        "pool_pre_ping": True,
        "pool_recycle": POOL_RECYCLE,
    }

# 创建异步引擎
engine = create_async_engine(
    db_url,
    **engine_kwargs,
)

# 创建异步会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖注入函数

    用法：
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库（创建表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()
