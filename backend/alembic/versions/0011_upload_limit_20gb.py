"""raise upload limits to 20gb

Revision ID: 0011_upload_limit_20gb
Revises: 0010_risk_engine_trc
Create Date: 2026-03-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0011_upload_limit_20gb'
down_revision = '0010_risk_engine_trc'
branch_labels = None
depends_on = None

DEFAULT_MAX_UPLOAD_BYTES = 20 * 1024 * 1024 * 1024
PREVIOUS_MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def upgrade() -> None:
    with op.batch_alter_table('org_security_policies') as batch_op:
        batch_op.alter_column(
            'max_upload_bytes',
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
            server_default=str(DEFAULT_MAX_UPLOAD_BYTES),
        )

    with op.batch_alter_table('pricing_plans') as batch_op:
        batch_op.alter_column(
            'max_upload_bytes',
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
            server_default=str(DEFAULT_MAX_UPLOAD_BYTES),
        )

    op.execute(
        sa.text(
            'UPDATE org_security_policies SET max_upload_bytes = :new_limit WHERE max_upload_bytes = :old_limit'
        ).bindparams(new_limit=DEFAULT_MAX_UPLOAD_BYTES, old_limit=PREVIOUS_MAX_UPLOAD_BYTES)
    )
    op.execute(
        sa.text(
            'UPDATE pricing_plans SET max_upload_bytes = :new_limit WHERE max_upload_bytes = :old_limit'
        ).bindparams(new_limit=DEFAULT_MAX_UPLOAD_BYTES, old_limit=PREVIOUS_MAX_UPLOAD_BYTES)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            'UPDATE org_security_policies SET max_upload_bytes = :old_limit WHERE max_upload_bytes = :new_limit'
        ).bindparams(new_limit=DEFAULT_MAX_UPLOAD_BYTES, old_limit=PREVIOUS_MAX_UPLOAD_BYTES)
    )
    op.execute(
        sa.text(
            'UPDATE pricing_plans SET max_upload_bytes = :old_limit WHERE max_upload_bytes = :new_limit'
        ).bindparams(new_limit=DEFAULT_MAX_UPLOAD_BYTES, old_limit=PREVIOUS_MAX_UPLOAD_BYTES)
    )

    with op.batch_alter_table('org_security_policies') as batch_op:
        batch_op.alter_column(
            'max_upload_bytes',
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
            server_default=str(PREVIOUS_MAX_UPLOAD_BYTES),
        )

    with op.batch_alter_table('pricing_plans') as batch_op:
        batch_op.alter_column(
            'max_upload_bytes',
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
            server_default=str(PREVIOUS_MAX_UPLOAD_BYTES),
        )
