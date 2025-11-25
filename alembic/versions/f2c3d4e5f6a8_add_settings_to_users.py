"""add settings to users

Revision ID: f2c3d4e5f6a8
Revises: f2c3d4e5f6a7
Create Date: 2025-11-24 23:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f2c3d4e5f6a8'
down_revision = 'f2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    """Add settings column to users table."""
    op.add_column('users', 
        sa.Column('settings', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json"))
    )
    # Remove server default after creation if we want to enforce application-level defaults only, 
    # but keeping it is fine too. The model has default={} which is application level.
    # To match model exactly (nullable=False), we need the data to be there.


def downgrade():
    """Remove settings column from users table."""
    op.drop_column('users', 'settings')
