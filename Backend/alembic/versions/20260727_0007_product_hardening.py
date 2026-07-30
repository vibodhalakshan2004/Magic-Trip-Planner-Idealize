"""Add planning jobs, versions, collaboration, shared cache, quota, and indexes."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260727_0007"
down_revision = "20260722_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "planning_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False, server_default="full_plan"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_stage", sa.String(length=120), nullable=False, server_default="Queued"),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_planning_jobs_user_idempotency"),
    )
    op.create_index("ix_planning_jobs_status_created", "planning_jobs", ["status", "created_at"])
    op.create_index("ix_planning_jobs_trip", "planning_jobs", ["trip_id", "created_at"])

    op.create_table(
        "trip_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("trip_id", "version_number", name="uq_trip_versions_number"),
    )
    op.create_index("ix_trip_versions_trip_created", "trip_versions", ["trip_id", "created_at"])

    op.create_table(
        "trip_collaborators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("trip_id", "user_id", name="uq_trip_collaborators_trip_user"),
    )
    op.create_index("ix_trip_collaborators_user", "trip_collaborators", ["user_id"])

    op.create_table(
        "external_cache",
        sa.Column("cache_key", sa.String(length=500), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_external_cache_expires", "external_cache", ["expires_at"])

    op.create_table(
        "google_api_usage",
        sa.Column("period", sa.String(length=7), primary_key=True),
        sa.Column("sku", sa.String(length=40), primary_key=True),
        sa.Column("used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_trips_user_updated", "trips", ["user_id", "updated_at"])
    op.create_index("ix_selected_places_trip", "selected_places", ["trip_id"])
    op.create_index("ix_selected_hotels_trip_day", "selected_hotels", ["trip_id", "day_number"])
    op.create_index("ix_route_plans_trip_created", "route_plans", ["trip_id", "created_at"])
    op.create_index("ix_budget_estimates_trip_created", "budget_estimates", ["trip_id", "created_at"])
    op.create_index("ix_reviews_user_created", "reviews", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_reviews_user_created", table_name="reviews")
    op.drop_index("ix_budget_estimates_trip_created", table_name="budget_estimates")
    op.drop_index("ix_route_plans_trip_created", table_name="route_plans")
    op.drop_index("ix_selected_hotels_trip_day", table_name="selected_hotels")
    op.drop_index("ix_selected_places_trip", table_name="selected_places")
    op.drop_index("ix_trips_user_updated", table_name="trips")
    op.drop_table("google_api_usage")
    op.drop_index("ix_external_cache_expires", table_name="external_cache")
    op.drop_table("external_cache")
    op.drop_index("ix_trip_collaborators_user", table_name="trip_collaborators")
    op.drop_table("trip_collaborators")
    op.drop_index("ix_trip_versions_trip_created", table_name="trip_versions")
    op.drop_table("trip_versions")
    op.drop_index("ix_planning_jobs_trip", table_name="planning_jobs")
    op.drop_index("ix_planning_jobs_status_created", table_name="planning_jobs")
    op.drop_table("planning_jobs")
