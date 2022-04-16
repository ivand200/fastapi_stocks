"""Delete from users column disable

Revision ID: 7c797e7f1fa7
Revises: 31f29fe08e75
Create Date: 2022-04-14 15:16:56.812514

"""
from alembic import op
import sqlalchemy as sa
from models import User


# revision identifiers, used by Alembic.
revision = '7c797e7f1fa7'
down_revision = '31f29fe08e75'
branch_labels = None
depends_on = None


def upgrade():
    # op.drop_column("users", "disable")
    op.add_column("users", sa.Column("role", sa.String(), nullable=True))
    op.drop_column("users", "disable")


def downgrade():
    pass
