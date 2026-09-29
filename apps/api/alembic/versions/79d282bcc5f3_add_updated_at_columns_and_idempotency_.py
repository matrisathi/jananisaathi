"""add updated_at columns and idempotency_key table

Revision ID: 79d282bcc5f3
Revises: 0002_app_role_grants
Create Date: 2026-09-29 04:05:57.458475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79d282bcc5f3'
down_revision: Union[str, None] = '0002_app_role_grants'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES_GETTING_UPDATED_AT = [
    "contact_method",
    "facility",
    "login_attempt",
    "organization",
    "organization_admin",
    "person",
    "pregnancy_episode",
    "refresh_token",
    "staff_membership",
    "staff_user",
]


def upgrade() -> None:
    op.create_table('idempotency_key',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('staff_user_id', sa.UUID(), nullable=False),
    sa.Column('endpoint', sa.String(length=100), nullable=False),
    sa.Column('key', sa.String(length=200), nullable=False),
    sa.Column('response_entity_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['staff_user_id'], ['staff_user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('staff_user_id', 'endpoint', 'key', name='uq_idempotency_key')
    )

    # server_default backfills existing rows (this table may already have
    # data); dropped afterward so future inserts rely on the application's
    # own default (app.models.base.utcnow) rather than a DB-side default.
    for table in TABLES_GETTING_UPDATED_AT:
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
    for table in TABLES_GETTING_UPDATED_AT:
        op.alter_column(table, "updated_at", server_default=None)

    # This table was created after 0002_app_role_grants' blanket grant ran,
    # so it needs its own — and going forward, ALTER DEFAULT PRIVILEGES
    # means any *future* table the migrator creates is automatically
    # readable/writable by the restricted app role too, without a
    # per-migration grant statement being remembered each time.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON idempotency_key TO matrisathi_app;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE matrisathi_migrator IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO matrisathi_app;"
    )


def downgrade() -> None:
    for table in TABLES_GETTING_UPDATED_AT:
        op.drop_column(table, "updated_at")
    op.drop_table('idempotency_key')
