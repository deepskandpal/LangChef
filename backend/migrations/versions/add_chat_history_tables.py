"""add_chat_history_tables

Revision ID: 005
Revises: 004
Create Date: 2023-03-18 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Create chats table
    op.create_table(
        'chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=True),
        sa.Column('model_provider', sa.String(), nullable=True),
        sa.Column('configuration', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('message_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes
    op.create_index(op.f('ix_chats_user_id'), 'chats', ['user_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_chat_id'), 'chat_messages', ['chat_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_order'), 'chat_messages', ['order'], unique=False)


def downgrade():
    # Drop tables in reverse order (children first)
    op.drop_index(op.f('ix_chat_messages_order'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_chat_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    
    op.drop_index(op.f('ix_chats_user_id'), table_name='chats')
    op.drop_table('chats') 