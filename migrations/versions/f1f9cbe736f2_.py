"""empty message

Revision ID: f1f9cbe736f2
Revises: 9dd048699017
Create Date: 2026-09-06 09:17:12.449908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1f9cbe736f2'
down_revision: Union[str, Sequence[str], None] = '9dd048699017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('messages',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('draft', sa.String(), nullable=False),
    sa.Column('draft_accepted', sa.Boolean(), nullable=True),
    sa.Column('content_sent', sa.String(), nullable=True),
    sa.Column('sent_at', sa.Date(), nullable=True),
    sa.Column('client_id', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # create the enum TYPE before anything can reference it
    result_enum = postgresql.ENUM('accepted', 'ignored', 'rejected', name='result')
    result_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('clients', sa.Column('result', result_enum, nullable=True))
    op.drop_column('clients', 'messaged_at')
    op.drop_column('clients', 'results')
    op.drop_column('clients', 'contacted')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('clients', sa.Column('contacted', sa.BOOLEAN(), autoincrement=False, nullable=False))

    results_enum = postgresql.ENUM('rejected', 'ignored', 'accepted', name='results')
    results_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('clients', sa.Column('results', results_enum, autoincrement=False, nullable=True))

    op.add_column('clients', sa.Column('messaged_at', sa.DATE(), autoincrement=False, nullable=True))
    op.drop_column('clients', 'result')

    # drop the type after nothing references it anymore
    result_enum = postgresql.ENUM('accepted', 'ignored', 'rejected', name='result')
    result_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_table('messages')
