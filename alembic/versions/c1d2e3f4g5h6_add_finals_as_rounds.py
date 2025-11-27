"""add finals as rounds

Revision ID: c1d2e3f4g5h6
Revises: ab15cf211903
Create Date: 2025-11-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = 'ab15cf211903'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add regular_rounds column
    op.add_column('tournaments', sa.Column('regular_rounds', sa.Integer(), nullable=True))
    
    # Add finals_started column
    op.add_column('tournaments', sa.Column('finals_started', sa.Boolean(), server_default='false', nullable=False))
    
    # Add finals_score column to tournament_participants
    op.add_column('tournament_participants', sa.Column('finals_score', sa.Float(), server_default='0', nullable=False))
    
    # Set regular_rounds = total_rounds for existing tournaments
    op.execute('UPDATE tournaments SET regular_rounds = total_rounds WHERE regular_rounds IS NULL')


def downgrade() -> None:
    op.drop_column('tournament_participants', 'finals_score')
    op.drop_column('tournaments', 'finals_started')
    op.drop_column('tournaments', 'regular_rounds')

