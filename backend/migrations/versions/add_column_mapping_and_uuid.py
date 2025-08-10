"""Add column_mapping and uuid fields

Revision ID: 006
Revises: 005
Create Date: 2023-03-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Add column_mapping to datasets table if it doesn't exist
    op.add_column('datasets', sa.Column('column_mapping', sa.JSON(), nullable=True), schema=None)
    
    # Add examples field to datasets table if it doesn't exist
    # Check if column exists first to avoid errors
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('datasets')]
    if 'examples' not in columns:
        op.add_column('datasets', sa.Column('examples', sa.JSON(), nullable=True), schema=None)
    
    # Add uuid field to dataset_items table
    op.add_column('dataset_items', sa.Column('uuid', sa.String(length=36), nullable=True), schema=None)
    
    # Create index on uuid field
    op.create_index(op.f('ix_dataset_items_uuid'), 'dataset_items', ['uuid'], unique=False)


def downgrade():
    # Drop index first
    op.drop_index(op.f('ix_dataset_items_uuid'), table_name='dataset_items')
    
    # Remove columns
    op.drop_column('dataset_items', 'uuid')
    op.drop_column('datasets', 'column_mapping')
    
    # Check if examples column exists before trying to drop it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('datasets')]
    if 'examples' in columns:
        op.drop_column('datasets', 'examples') 