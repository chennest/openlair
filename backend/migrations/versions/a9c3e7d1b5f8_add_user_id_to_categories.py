"""add user_id to categories for custom categories

Revision ID: a9c3e7d1b5f8
Revises: b8c4d6e8f0a2
Create Date: 2026-09-10 08:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9c3e7d1b5f8'
down_revision: Union[str, Sequence[str], None] = 'b8c4d6e8f0a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # user_id NULL = 系统预置；非 NULL = 用户自定义（仅创建者可改删）
    op.add_column('categories', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index('ix_categories_user_id', 'categories', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # 回退前会连带丢弃用户自定义分类（无流水迁移动作；流水引用的分类名仍可由应用层兜底「其他」）
    op.drop_index('ix_categories_user_id', table_name='categories')
    op.drop_column('categories', 'user_id')
