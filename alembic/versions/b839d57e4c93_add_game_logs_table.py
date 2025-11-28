"""add_game_logs_table

Revision ID: b839d57e4c93
Revises: c1d2e3f4g5h6
Create Date: 2025-11-28 03:03:50.051443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b839d57e4c93'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'game_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('game_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('user_battletag', sa.String(), nullable=False),
        sa.Column('user_role', sa.String(), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('action_description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['tournament_games.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_game_logs_id'), 'game_logs', ['id'], unique=False)
    op.create_index(op.f('ix_game_logs_game_id'), 'game_logs', ['game_id'], unique=False)
    op.create_index(op.f('ix_game_logs_action_type'), 'game_logs', ['action_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_game_logs_action_type'), table_name='game_logs')
    op.drop_index(op.f('ix_game_logs_game_id'), table_name='game_logs')
    op.drop_index(op.f('ix_game_logs_id'), table_name='game_logs')
    op.drop_table('game_logs')
