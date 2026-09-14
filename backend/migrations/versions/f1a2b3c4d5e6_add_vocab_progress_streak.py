"""add vocab progress streak columns

Revision ID: f1a2b3c4d5e6
Revises: d5e6f7a8b9c0
Create Date: 2026-09-14 20:50:00.000000

「是否掌握」从 FSRS 的 stability 改成显式的连续答对次数：
- correct_streak  连续答对次数（答对 +1，答错清零）
- required_streak 该词要求的连续答对次数（首次识词判断对=3，判断错/不认识=5；0=还没判断过）
- identify_result 首次识词判断结果（'' 未判断 / know / unsure）

为什么需要：原来的 Scheduler(learning_steps=()) 是空学习步，答对一次就直接
state=Review 并排到 2 天后，再连对两次就拉到 45 天 —— 体感上等于「答对一次 = 已掌握」。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'vocab_word_progress',
        sa.Column('correct_streak', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'vocab_word_progress',
        sa.Column('required_streak', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'vocab_word_progress',
        sa.Column('identify_result', sa.String(length=10), nullable=False, server_default=''),
    )

    # 历史行回填：**只给真正作答过的行**（last_review 非空）补上「熟悉的词」这档要求，
    # 让它们进入次数判定；只收藏 / 只标已掌握的空进度行保持 required_streak=0，
    # 下次作答才充当那次「首次识词判断」。
    # correct_streak 一律从 0 起步 —— 老数据没有连对记录，从头数起最保守（宁可多复习几遍）。
    # identify_result 保持空串：历史数据没有判断记录，不伪造。
    op.execute(
        "UPDATE vocab_word_progress SET required_streak = 3 "
        "WHERE required_streak = 0 AND last_review IS NOT NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('vocab_word_progress', 'identify_result')
    op.drop_column('vocab_word_progress', 'required_streak')
    op.drop_column('vocab_word_progress', 'correct_streak')
