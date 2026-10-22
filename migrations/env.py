from logging.config import fileConfig
import asyncio
from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from app.models import Base
from app.config import settings
config=context.config
config.set_main_option('sqlalchemy.url',settings.database_url.replace('%','%%'))
target_metadata=Base.metadata

def offline():
    context.configure(url=settings.database_url,target_metadata=target_metadata,literal_binds=True,dialect_opts={'paramstyle':'named'})
    with context.begin_transaction():context.run_migrations()

async def online():
    connectable=async_engine_from_config(config.get_section(config.config_ini_section),prefix='sqlalchemy.',poolclass=pool.NullPool)
    async with connectable.connect() as conn:
        await conn.run_sync(lambda connection: (context.configure(connection=connection,target_metadata=target_metadata),context.run_migrations()))
    await connectable.dispose()

if context.is_offline_mode():offline()
else:asyncio.run(online())
