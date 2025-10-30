"""Initial schema with user settings

Revision ID: 001
Revises:
Create Date: 2025-01-30 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='Europe/Moscow'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_poll_time', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True)

    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('emoji', sa.String(length=10), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uix_user_category_name')
    )
    op.create_index(op.f('ix_categories_user_id'), 'categories', ['user_id'], unique=False)

    # Create activities table
    op.create_table(
        'activities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('start_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('end_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('end_time > start_time', name='check_end_time_after_start'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activities_user_id'), 'activities', ['user_id'], unique=False)
    op.create_index(op.f('ix_activities_start_time'), 'activities', ['start_time'], unique=False)
    op.create_index(op.f('ix_activities_end_time'), 'activities', ['end_time'], unique=False)

    # Create user_settings table (Step 2)
    op.create_table(
        'user_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('poll_interval_weekday', sa.Integer(), nullable=False, server_default='120'),
        sa.Column('poll_interval_weekend', sa.Integer(), nullable=False, server_default='180'),
        sa.Column('quiet_hours_start', sa.Time(), nullable=True, server_default="'23:00:00'"),
        sa.Column('quiet_hours_end', sa.Time(), nullable=True, server_default="'07:00:00'"),
        sa.Column('reminder_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('reminder_delay_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_settings_user_id'), 'user_settings', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_settings_user_id'), table_name='user_settings')
    op.drop_table('user_settings')

    op.drop_index(op.f('ix_activities_end_time'), table_name='activities')
    op.drop_index(op.f('ix_activities_start_time'), table_name='activities')
    op.drop_index(op.f('ix_activities_user_id'), table_name='activities')
    op.drop_table('activities')

    op.drop_index(op.f('ix_categories_user_id'), table_name='categories')
    op.drop_table('categories')

    op.drop_index(op.f('ix_users_telegram_id'), table_name='users')
    op.drop_table('users')
