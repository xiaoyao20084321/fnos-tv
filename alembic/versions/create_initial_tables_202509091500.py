"""创建初始数据库表

Revision ID: create_initial_tables
Revises: ba791c53110e
Create Date: 2025-09-09 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'create_initial_tables'
down_revision: Union[str, Sequence[str], None] = 'ba791c53110e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建数据库表."""
    # 创建 record 表
    op.create_table('record',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('guid', sa.String(), nullable=True),
        sa.Column('episode_guid', sa.String(), nullable=True),
        sa.Column('time', sa.Integer(), nullable=True),
        sa.Column('create_time', sa.Integer(), nullable=True),
        sa.Column('playback_speed', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建 video_config_list 表
    op.create_table('video_config_list',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('guid', sa.String(), nullable=True),
        sa.Column('startTime', sa.Integer(), nullable=True),
        sa.Column('endTime', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建 video_config_url 表 (包含新增的 parent_guid 字段)
    op.create_table('video_config_url',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('guid', sa.String(), nullable=True),
        sa.Column('parent_guid', sa.String(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """删除数据库表."""
    op.drop_table('video_config_url')
    op.drop_table('video_config_list')
    op.drop_table('record')