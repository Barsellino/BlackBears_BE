"""add_tournament_logs_table

Revision ID: 4752f0caf6df
Revises: b839d57e4c93
Create Date: 2025-11-28 03:36:30.001277

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4752f0caf6df'
down_revision: Union[str, Sequence[str], None] = 'b839d57e4c93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tournament_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('user_battletag', sa.String(), nullable=False),
        sa.Column('user_role', sa.String(), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('action_description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tournament_logs_id'), 'tournament_logs', ['id'], unique=False)
    op.create_index(op.f('ix_tournament_logs_tournament_id'), 'tournament_logs', ['tournament_id'], unique=False)
    op.create_index(op.f('ix_tournament_logs_action_type'), 'tournament_logs', ['action_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tournament_logs_action_type'), table_name='tournament_logs')
    op.drop_index(op.f('ix_tournament_logs_tournament_id'), table_name='tournament_logs')
    op.drop_index(op.f('ix_tournament_logs_id'), table_name='tournament_logs')
    op.drop_table('tournament_logs')
