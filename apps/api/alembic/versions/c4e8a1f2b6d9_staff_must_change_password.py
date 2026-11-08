"""staff must change password after an admin sets it

Accounts created (or reset) by an organization admin get a temporary
password and must set their own at first sign-in. No grant change: the app
role already holds table-level rights on staff_user (tests/test_db_grants.py).

Revision ID: c4e8a1f2b6d9
Revises: a8b3d5e1f407
Create Date: 2026-11-07 22:10:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e8a1f2b6d9"
down_revision: Union[str, None] = "a8b3d5e1f407"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "staff_user",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("staff_user", "must_change_password")
