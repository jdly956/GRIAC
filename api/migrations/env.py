import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL absente : les migrations exigent une URL PostgreSQL fournie par "
        "l'environnement (ex. postgresql+psycopg://sia:...@postgres:5432/sia). "
        "Aucune URL n'est jamais écrite en dur (contrainte CLAUDE.md)."
    )

# Pas encore de modèles ORM (les tables arrivent avec S1.7/S1.11).
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(url=database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
