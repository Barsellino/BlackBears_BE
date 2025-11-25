"""add telegram to users

Revision ID: 007592814a89
Revises: f2c3d4e5f6a8
Create Date: 2025-11-25 04:13:22.226364

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007592814a89'
down_revision: Union[str, Sequence[str], None] = 'f2c3d4e5f6a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('telegram', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'telegram')
