"""Add AWS credentials to User model

Revision ID: 003
Revises: 002
Create Date: 2023-07-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add AWS credentials columns to the users table
    op.add_column('users', sa.Column('aws_access_key_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('aws_secret_access_key', sa.String(), nullable=True))
    op.add_column('users', sa.Column('aws_session_token', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('aws_token_expiry', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove AWS credentials columns from the users table
    op.drop_column('users', 'aws_token_expiry')
    op.drop_column('users', 'aws_session_token')
    op.drop_column('users', 'aws_secret_access_key')
    op.drop_column('users', 'aws_access_key_id') 