"""assistant session compaction summary

Revision ID: f1e2d3c4b5a6
Revises: ef1c48d8ee84
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1e2d3c4b5a6'
down_revision: Union[str, Sequence[str], None] = 'ef1c48d8ee84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('assistant_sessions', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('assistant_sessions', sa.Column('summary_through_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('assistant_sessions', 'summary_through_id')
    op.drop_column('assistant_sessions', 'summary')
