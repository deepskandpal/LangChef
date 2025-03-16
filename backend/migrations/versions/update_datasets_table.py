"""Update datasets table

Revision ID: 004
Revises: 003
Create Date: 2023-03-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ENUM


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'  # Previous migration was 003
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create dataset_type enum if it doesn't exist
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if 'datasettype' not in inspector.get_enums():
        dataset_type_enum = sa.Enum('text', 'json', 'csv', 'jsonl', 'custom', name='datasettype')
        dataset_type_enum.create(connection)
    
    # Use ALTER TABLE to modify the existing datasets table
    # First, check if the 'type' column exists
    if 'type' not in [col['name'] for col in inspector.get_columns('datasets')]:
        # Add the type column using the enum
        op.add_column('datasets', sa.Column('type', sa.Enum('text', 'json', 'csv', 'jsonl', 'custom', name='datasettype'), nullable=True))
        # Set a default value for existing records
        op.execute("UPDATE datasets SET type = 'json'::datasettype")
        # Make the column not nullable
        op.alter_column('datasets', 'type', nullable=False)
    
    # Check for is_active column
    if 'is_active' not in [col['name'] for col in inspector.get_columns('datasets')]:
        op.add_column('datasets', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))
        op.execute("UPDATE datasets SET is_active = true")
        op.alter_column('datasets', 'is_active', nullable=False)
    
    # Check for meta_data column
    if 'meta_data' not in [col['name'] for col in inspector.get_columns('datasets')]:
        op.add_column('datasets', sa.Column('meta_data', JSONB, nullable=True))
    
    # Create dataset_items table if it doesn't exist
    if 'dataset_items' not in inspector.get_table_names():
        op.create_table(
            'dataset_items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('dataset_id', sa.Integer(), nullable=False),
            sa.Column('content', JSONB, nullable=False),
            sa.Column('meta_data', JSONB, nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    
    # Create dataset_versions table if it doesn't exist
    if 'dataset_versions' not in inspector.get_table_names():
        op.create_table(
            'dataset_versions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('dataset_id', sa.Integer(), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False),
            sa.Column('meta_data', JSONB, nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    # We can't simply drop columns in a downgrade without potentially losing data
    # This is a simplified downgrade that doesn't attempt to restore the original state
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Drop dataset_versions table if it exists
    if 'dataset_versions' in inspector.get_table_names():
        op.drop_table('dataset_versions')
    
    # Drop dataset_items table if it exists  
    if 'dataset_items' in inspector.get_table_names():
        op.drop_table('dataset_items')
    
    # Remove added columns if they exist
    columns = [col['name'] for col in inspector.get_columns('datasets')]
    if 'meta_data' in columns:
        op.drop_column('datasets', 'meta_data')
    if 'is_active' in columns:
        op.drop_column('datasets', 'is_active')
    if 'type' in columns:
        op.drop_column('datasets', 'type')
        
    # Drop the enum
    op.execute("DROP TYPE IF EXISTS datasettype;") 