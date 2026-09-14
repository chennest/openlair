"""add vocab daily goals and progress.first_learned_at

Revision ID: d5e6f7a8b9c0
Revises: c9042b44cc6e
Create Date: 2026-09-14 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'c9042b44cc6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 每人一条的背词每日目标（user_id 唯一，不预建行：取不到时服务层回缺省值）
    op.create_table(
        'vocab_daily_goals',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('new_target', sa.Integer(), nullable=False),
        sa.Column('review_target', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_vocab_daily_goals_user_id'), 'vocab_daily_goals', ['user_id'], unique=True)

    # 「今日已记」的计数依据：首次真正作答的时刻（仅 submit_answer 写入）
    op.add_column('vocab_word_progress', sa.Column('first_learned_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        op.f('ix_vocab_word_progress_first_learned_at'),
        'vocab_word_progress',
        ['first_learned_at'],
        unique=False,
    )
    # 历史行回填：老数据没有首学时间，用进度行的创建时刻近似。
    # 但**只回填真正作答过的行**（last_review 非空）—— 只收藏 / 只标已掌握的空进度行
    # 按新口径本来就不算「记住这个词」，填上反而会把迁移当天的「今日已记」灌高。
    op.execute(
        "UPDATE vocab_word_progress SET first_learned_at = created_at "
        "WHERE first_learned_at IS NULL AND last_review IS NOT NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_vocab_word_progress_first_learned_at'), table_name='vocab_word_progress')
    op.drop_column('vocab_word_progress', 'first_learned_at')
    op.drop_index(op.f('ix_vocab_daily_goals_user_id'), table_name='vocab_daily_goals')
    op.drop_table('vocab_daily_goals')
