"""add inventory items, stock movements, order line inventory link, settings low stock threshold

Revision ID: 648c6b9841b9
Revises: e4b26f221d0b
Create Date: 2026-08-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '648c6b9841b9'
down_revision = 'e4b26f221d0b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('inventory_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('sku', sa.String(length=64), nullable=True),
    sa.Column('category', sa.String(length=32), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('unit', sa.String(length=16), nullable=False),
    sa.Column('default_price', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('default_vat_rate', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('quantity_on_hand', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('low_stock_threshold', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('inventory_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_inventory_items_category'), ['category'], unique=False)

    with op.batch_alter_table('order_lines', schema=None) as batch_op:
        batch_op.add_column(sa.Column('inventory_item_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_order_lines_inventory_item_id_inventory_items',
            'inventory_items', ['inventory_item_id'], ['id'],
        )

    op.create_table('stock_movements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('inventory_item_id', sa.Integer(), nullable=False),
    sa.Column('order_line_id', sa.Integer(), nullable=True),
    sa.Column('quantity_delta', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('reason', sa.String(length=20), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name='fk_stock_movements_created_by_id_users'),
    sa.ForeignKeyConstraint(['inventory_item_id'], ['inventory_items.id'], name='fk_stock_movements_inventory_item_id_inventory_items'),
    sa.ForeignKeyConstraint(['order_line_id'], ['order_lines.id'], name='fk_stock_movements_order_line_id_order_lines', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('stock_movements', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_stock_movements_inventory_item_id'), ['inventory_item_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_stock_movements_order_line_id'), ['order_line_id'], unique=False)

    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('default_low_stock_threshold', sa.Numeric(precision=10, scale=2),
                      nullable=False, server_default='5.00')
        )

    # Server default above exists only to backfill the existing settings row
    # (id=1); future inserts rely on the Python-side model default, per the
    # same pattern used in 94e0f9b7a670.
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.alter_column('default_low_stock_threshold', server_default=None)


def downgrade():
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.drop_column('default_low_stock_threshold')

    with op.batch_alter_table('stock_movements', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_stock_movements_order_line_id'))
        batch_op.drop_index(batch_op.f('ix_stock_movements_inventory_item_id'))

    op.drop_table('stock_movements')

    with op.batch_alter_table('order_lines', schema=None) as batch_op:
        batch_op.drop_constraint('fk_order_lines_inventory_item_id_inventory_items', type_='foreignkey')
        batch_op.drop_column('inventory_item_id')

    with op.batch_alter_table('inventory_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_inventory_items_category'))

    op.drop_table('inventory_items')
