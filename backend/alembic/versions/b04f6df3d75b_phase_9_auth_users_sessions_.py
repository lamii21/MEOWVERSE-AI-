"""phase 9 auth users sessions achievements and cat_analyses ownership

Revision ID: b04f6df3d75b
Revises: d64ea3d2f0bd
Create Date: 2026-08-11 14:33:25.520072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b04f6df3d75b'
down_revision: Union[str, None] = 'd64ea3d2f0bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FK_NAME = "fk_cat_analyses_user_id_users"


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('password_hash', sa.String(length=60), nullable=False),
        sa.Column('display_name', sa.String(length=60), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table(
        'sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sessions_token_hash'), 'sessions', ['token_hash'], unique=True)
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)

    op.create_table(
        'user_achievements',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('achievement_key', sa.String(length=50), nullable=False),
        sa.Column('unlocked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'achievement_key', name='uq_user_achievement'),
    )
    op.create_index(op.f('ix_user_achievements_user_id'), 'user_achievements', ['user_id'], unique=False)

    op.add_column('cat_analyses', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('cat_analyses', sa.Column('user_id', sa.Uuid(), nullable=True))
    # cat_name/rarity land NOT NULL, but 341 pre-existing rows (from
    # Phases 7-8 dev testing) predate these columns — add them nullable,
    # backfill from the JSONB `profile` column (which has always carried
    # this data, just not as queryable top-level columns — see
    # CatAnalysisModel's docstring), *then* enforce NOT NULL. This is
    # "preserve existing data" (Phase 9 spec §1), not a fresh baseline.
    op.add_column('cat_analyses', sa.Column('cat_name', sa.String(length=40), nullable=True))
    op.add_column('cat_analyses', sa.Column('rarity', sa.String(length=20), nullable=True))
    op.execute(
        "UPDATE cat_analyses SET cat_name = profile->>'name', rarity = profile->>'rarity' "
        "WHERE cat_name IS NULL"
    )
    op.alter_column('cat_analyses', 'cat_name', nullable=False)
    op.alter_column('cat_analyses', 'rarity', nullable=False)

    op.add_column('cat_analyses', sa.Column('image_url', sa.String(length=500), nullable=True))
    op.add_column('cat_analyses', sa.Column('is_favorite', sa.Boolean(), server_default='false', nullable=False))
    op.create_index('ix_cat_analyses_user_id_created_at', 'cat_analyses', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_cat_analyses_user_id_rarity', 'cat_analyses', ['user_id', 'rarity'], unique=False)
    op.create_foreign_key(_FK_NAME, 'cat_analyses', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint(_FK_NAME, 'cat_analyses', type_='foreignkey')
    op.drop_index('ix_cat_analyses_user_id_rarity', table_name='cat_analyses')
    op.drop_index('ix_cat_analyses_user_id_created_at', table_name='cat_analyses')
    op.drop_column('cat_analyses', 'is_favorite')
    op.drop_column('cat_analyses', 'image_url')
    op.drop_column('cat_analyses', 'rarity')
    op.drop_column('cat_analyses', 'cat_name')
    op.drop_column('cat_analyses', 'user_id')
    op.drop_column('cat_analyses', 'updated_at')
    op.drop_index(op.f('ix_user_achievements_user_id'), table_name='user_achievements')
    op.drop_table('user_achievements')
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_token_hash'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
