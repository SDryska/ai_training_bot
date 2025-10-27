"""initial_schema

Revision ID: b66012ceafd1
Revises: 
Create Date: 2025-10-26 13:56:59.750586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b66012ceafd1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Таблица для истории диалогов
    op.create_table(
        'conversations',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger, nullable=False),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_conversations_user_provider', 'conversations',
                    ['user_id', 'provider_type', 'finished_at', 'created_at'])
    
    # Таблица для FSM состояний
    op.create_table(
        'fsm_storage',
        sa.Column('storage_key', sa.String(255), primary_key=True),
        sa.Column('bot_id', sa.BigInteger, nullable=True),
        sa.Column('chat_id', sa.BigInteger, nullable=True),
        sa.Column('user_id', sa.BigInteger, nullable=True),
        sa.Column('state', sa.String(255), nullable=True),
        sa.Column('data', sa.JSON, nullable=False, server_default='{}'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_fsm_storage_user', 'fsm_storage', ['user_id', 'updated_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_fsm_storage_user', table_name='fsm_storage')
    op.drop_table('fsm_storage')
    op.drop_index('idx_conversations_user_provider', table_name='conversations')
    op.drop_table('conversations')
