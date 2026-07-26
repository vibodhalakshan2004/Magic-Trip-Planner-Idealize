"""add media fields for selected places and hotels

Revision ID: 20260619_0003
Revises: 20260619_0002
Create Date: 2026-06-19 01:30:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260619_0003"
down_revision = "20260619_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    place_columns = {
        column["name"]
        for column in inspector.get_columns("selected_places")
    }
    hotel_columns = {
        column["name"]
        for column in inspector.get_columns("selected_hotels")
    }

    if "image_url" not in place_columns:
        op.add_column(
            "selected_places",
            sa.Column("image_url", sa.String(), nullable=True),
        )
    if "short_description" not in hotel_columns:
        op.add_column(
            "selected_hotels",
            sa.Column("short_description", sa.String(), nullable=True),
        )
    if "image_url" not in hotel_columns:
        op.add_column(
            "selected_hotels",
            sa.Column("image_url", sa.String(), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    place_columns = {
        column["name"]
        for column in inspector.get_columns("selected_places")
    }
    hotel_columns = {
        column["name"]
        for column in inspector.get_columns("selected_hotels")
    }

    if "image_url" in hotel_columns:
        op.drop_column("selected_hotels", "image_url")
    if "short_description" in hotel_columns:
        op.drop_column("selected_hotels", "short_description")
    if "image_url" in place_columns:
        op.drop_column("selected_places", "image_url")
