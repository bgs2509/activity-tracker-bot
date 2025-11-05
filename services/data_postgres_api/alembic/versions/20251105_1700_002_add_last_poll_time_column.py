"""Add last_poll_time column to users table

Revision ID: 002
Revises: 001
Create Date: 2025-11-05 17:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add last_poll_time column to users table."""
    op.add_column(
        'users',
        sa.Column('last_poll_time', sa.TIMESTAMP(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove last_poll_time column from users table."""
    op.drop_column('users', 'last_poll_time')
