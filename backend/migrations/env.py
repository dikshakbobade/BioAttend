from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import models
from app.models.models import Base

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    # Use sync URL for migrations
    # Load from environment
    import os
    from dotenv import load_dotenv
    load_dotenv()
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    
    # Convert async URL to sync for migrations
    if "sqlite+aiosqlite" in url:
        sync_url = url.replace("sqlite+aiosqlite", "sqlite")
    elif "mysql+aiomysql" in url:
        sync_url = url.replace("mysql+aiomysql", "mysql+pymysql")
    else:
        sync_url = url.replace("postgresql+asyncpg://", "postgresql://")
    
    connectable = engine_from_config(
        {"sqlalchemy.url": sync_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()