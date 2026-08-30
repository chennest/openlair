"""add invite_code to books

Revision ID: 4d8f9a0b1c2d
Revises: f1e2d3c4b5a6
Create Date: 2026-08-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d8f9a0b1c2d'
down_revision: Union[str, Sequence[str], None] = 'f1e2d3c4b5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('books', sa.Column('invite_code', sa.String(length=12), nullable=True))
    op.create_index(op.f('ix_books_invite_code'), 'books', ['invite_code'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_books_invite_code'), table_name='books')
    op.drop_column('books', 'invite_code')
