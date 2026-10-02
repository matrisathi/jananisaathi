"""person intake fields, contact verification attribution, atomic idempotency claims

Revision ID: 67ca239c7fe7
Revises: 79d282bcc5f3
Create Date: 2026-09-30 05:55:41.204188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67ca239c7fe7'
down_revision: Union[str, None] = '79d282bcc5f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('contact_method', sa.Column('verified_by_staff_user_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_contact_method_verified_by_staff_user_id', 'contact_method', 'staff_user',
        ['verified_by_staff_user_id'], ['id'],
    )
    # idempotency_key is created and dropped within this same deployment's
    # lifetime by request activity, not seeded — safe to add NOT NULL
    # without a backfill default.
    op.add_column('idempotency_key', sa.Column('payload_hash', sa.String(length=64), nullable=False))
    op.alter_column('idempotency_key', 'response_entity_id',
               existing_type=sa.UUID(),
               nullable=True)

    # age_precision backfills existing Person rows as UNKNOWN (the honest
    # default — we don't actually know their prior precision), then drops
    # the server default so future inserts rely on the application default.
    age_precision_enum = sa.Enum(
        'EXACT_DOB', 'YEAR_ONLY', 'APPROXIMATE_AGE', 'UNKNOWN', name='age_precision'
    )
    age_precision_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'person',
        sa.Column('age_precision', age_precision_enum, nullable=False, server_default='UNKNOWN'),
    )
    op.alter_column('person', 'age_precision', server_default=None)
    op.add_column('person', sa.Column('birth_year', sa.Integer(), nullable=True))
    op.add_column('person', sa.Column('reported_age_years', sa.Integer(), nullable=True))
    op.add_column('person', sa.Column('reported_medical_history', sa.String(length=2000), nullable=True))
    op.add_column('person', sa.Column('known_allergies_medicines', sa.String(length=2000), nullable=True))


def downgrade() -> None:
    op.drop_column('person', 'known_allergies_medicines')
    op.drop_column('person', 'reported_medical_history')
    op.drop_column('person', 'reported_age_years')
    op.drop_column('person', 'birth_year')
    op.drop_column('person', 'age_precision')
    sa.Enum(name='age_precision').drop(op.get_bind(), checkfirst=True)
    op.alter_column('idempotency_key', 'response_entity_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('idempotency_key', 'payload_hash')
    op.drop_constraint('fk_contact_method_verified_by_staff_user_id', 'contact_method', type_='foreignkey')
    op.drop_column('contact_method', 'verified_by_staff_user_id')
