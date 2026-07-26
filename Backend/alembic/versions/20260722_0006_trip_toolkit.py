"""Add persistent traveler toolkit fields to trips."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260722_0006"
down_revision = "20260721_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trips",
        sa.Column("traveler_notes", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "trips",
        sa.Column("emergency_contact", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "trips",
        sa.Column(
            "checklist",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "trips",
        sa.Column(
            "expenses",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("trips", "expenses")
    op.drop_column("trips", "checklist")
    op.drop_column("trips", "emergency_contact")
    op.drop_column("trips", "traveler_notes")

