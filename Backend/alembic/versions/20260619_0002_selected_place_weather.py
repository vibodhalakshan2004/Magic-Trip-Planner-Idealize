"""add selected place weather summary

Revision ID: 20260619_0002
Revises: 20260619_0001
Create Date: 2026-06-19 00:30:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260619_0002"
down_revision = "20260619_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("selected_places")
    }
    if "weather_summary" not in columns:
        op.add_column(
            "selected_places",
            sa.Column("weather_summary", sa.String(), nullable=True),
        )


def downgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("selected_places")
    }
    if "weather_summary" in columns:
        op.drop_column("selected_places", "weather_summary")
