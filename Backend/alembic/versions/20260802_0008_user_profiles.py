"""Add editable user profile picture fields."""

import sqlalchemy as sa

from alembic import op

revision = "20260802_0008"
down_revision = "20260727_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_picture", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("profile_picture_content_type", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("profile_picture_version", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("profile_picture_updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_picture_updated_at")
    op.drop_column("users", "profile_picture_version")
    op.drop_column("users", "profile_picture_content_type")
    op.drop_column("users", "profile_picture")
