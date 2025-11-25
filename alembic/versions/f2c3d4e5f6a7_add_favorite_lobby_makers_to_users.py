"""add favorite_lobby_makers column to users

Revision ID: f2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-11-24 23:30:09.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade():
    """Add favorite_lobby_makers column to users table."""
    op.add_column('users', sa.Column('favorite_lobby_makers', postgresql.JSON(), nullable=True))

def downgrade():
    """Remove favorite_lobby_makers column from users table."""
    op.drop_column('users', 'favorite_lobby_makers')
