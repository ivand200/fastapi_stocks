"""Add ma10 to etf

Revision ID: be9d11fba3e0
Revises: a7ebbd804f8f
Create Date: 2022-04-14 18:07:52.949418

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'be9d11fba3e0'
down_revision = 'a7ebbd804f8f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("etf", sa.Column("ma10", sa.Float(), nullable=True))


def downgrade():
    pass
