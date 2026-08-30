"""add settings table (system settings key-value)

Revision ID: b8c4d6e8f0a2
Revises: a7b3c5d9e1f2
Create Date: 2026-08-30 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c4d6e8f0a2'
down_revision: Union[str, Sequence[str], None] = 'a7b3c5d9e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('setting_key', sa.String(length=64), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_settings_setting_key'), 'settings', ['setting_key'], unique=True)
    # 默认禁止注册（"0"=禁止 / "1"=允许），生产如需开放手动 UPDATE
    op.execute(
        "INSERT INTO settings (setting_key, value, updated_at) "
        "VALUES ('allow_register', '0', CURRENT_TIMESTAMP)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_settings_setting_key'), table_name='settings')
    op.drop_table('settings')
