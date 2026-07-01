"""
Alembic 环境配置

用于数据库迁移管理
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.database import Base

# 导入所有模型以确保它们被注册到 Base.metadata
from app.models import *  # noqa: F401, F403

# Alembic Config 对象
config = context.config

# 设置数据库 URL
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 元数据对象，用于自动生成迁移
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    在 'offline' 模式下运行迁移。

    这种模式下不需要数据库连接，只生成 SQL 脚本。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """执行迁移"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # 扩展支持
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    在 'online' 模式下运行异步迁移。

    创建异步引擎并执行迁移。
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    在 'online' 模式下运行迁移。

    连接到数据库并执行迁移。
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
