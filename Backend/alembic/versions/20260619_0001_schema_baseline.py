"""schema baseline

Revision ID: 20260619_0001
Revises: 
Create Date: 2026-06-19 00:00:00

"""

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260619_0001"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    if context.is_offline_mode():
        return False

    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _has_column(bind, table_name: str, column_name: str) -> bool:
    if context.is_offline_mode():
        return False

    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "users"):
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )

    if not _has_table(bind, "preferences"):
        op.create_table(
            "preferences",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("travel_style", sa.String(), nullable=True),
            sa.Column("food_preference", sa.String(), nullable=True),
            sa.Column(
                "interests",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column("preferred_transport", sa.String(), nullable=True),
            sa.Column("preferred_hotel_type", sa.String(), nullable=True),
            sa.Column("budget_min", sa.Integer(), nullable=True),
            sa.Column("budget_max", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )
        op.alter_column("preferences", "interests", server_default=None)
    elif not _has_column(bind, "preferences", "interests"):
        op.add_column(
            "preferences",
            sa.Column(
                "interests",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
        op.alter_column("preferences", "interests", server_default=None)

    if not _has_table(bind, "trips"):
        op.create_table(
            "trips",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("start_location", sa.String(), nullable=False),
            sa.Column("destination", sa.String(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("budget_min", sa.Integer(), nullable=False),
            sa.Column("budget_max", sa.Integer(), nullable=False),
            sa.Column("travelers", sa.Integer(), nullable=False),
            sa.Column("transport_type", sa.String(), nullable=False),
            sa.Column("trip_status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(bind, "reviews"):
        op.create_table(
            "reviews",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("place_name", sa.String(), nullable=False),
            sa.Column("place_type", sa.String(), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("review_text", sa.Text(), nullable=False),
            sa.Column("visit_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(bind, "selected_places"):
        op.create_table(
            "selected_places",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("place_key", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("short_description", sa.String(), nullable=True),
            sa.Column("reason_for_recommendation", sa.String(), nullable=True),
            sa.Column("best_time_to_visit", sa.String(), nullable=True),
            sa.Column("estimated_visit_duration_hours", sa.Float(), nullable=False),
            sa.Column("estimated_cost_lkr_per_person", sa.Float(), nullable=False),
            sa.Column("priority_score", sa.Integer(), nullable=False),
            sa.Column(
                "suitable_for",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "warnings",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column("search_query", sa.String(), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.alter_column("selected_places", "suitable_for", server_default=None)
        op.alter_column("selected_places", "warnings", server_default=None)

    if not _has_table(bind, "selected_hotels"):
        op.create_table(
            "selected_hotels",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("hotel_key", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("hotel_type", sa.String(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("area", sa.String(), nullable=True),
            sa.Column("check_in_date", sa.Date(), nullable=True),
            sa.Column("check_out_date", sa.Date(), nullable=True),
            sa.Column("nights", sa.Integer(), nullable=False),
            sa.Column("rooms", sa.Integer(), nullable=False),
            sa.Column("estimated_price_per_night_lkr", sa.Float(), nullable=False),
            sa.Column("total_estimated_price_lkr", sa.Float(), nullable=False),
            sa.Column("rating_estimate", sa.Float(), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("distance_summary", sa.String(), nullable=True),
            sa.Column("reason_for_recommendation", sa.String(), nullable=True),
            sa.Column(
                "amenities",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "warnings",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column("search_query", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.alter_column("selected_hotels", "amenities", server_default=None)
        op.alter_column("selected_hotels", "warnings", server_default=None)

    if not _has_table(bind, "budget_estimates"):
        op.create_table(
            "budget_estimates",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("days", sa.Integer(), nullable=False),
            sa.Column("nights", sa.Integer(), nullable=False),
            sa.Column("travelers", sa.Integer(), nullable=False),
            sa.Column("budget_min_lkr", sa.Float(), nullable=False),
            sa.Column("budget_max_lkr", sa.Float(), nullable=False),
            sa.Column("selected_places_cost_lkr", sa.Float(), nullable=False),
            sa.Column("hotel_cost_lkr", sa.Float(), nullable=False),
            sa.Column("food_cost_lkr", sa.Float(), nullable=False),
            sa.Column("transport_cost_lkr", sa.Float(), nullable=False),
            sa.Column("other_cost_lkr", sa.Float(), nullable=False),
            sa.Column("subtotal_lkr", sa.Float(), nullable=False),
            sa.Column("buffer_lkr", sa.Float(), nullable=False),
            sa.Column("total_estimated_cost_lkr", sa.Float(), nullable=False),
            sa.Column("remaining_budget_lkr", sa.Float(), nullable=False),
            sa.Column("over_budget_amount_lkr", sa.Float(), nullable=False),
            sa.Column("budget_status", sa.String(), nullable=False),
            sa.Column(
                "breakdown",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "warnings",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "suggestions",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column("summary", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.alter_column("budget_estimates", "breakdown", server_default=None)
        op.alter_column("budget_estimates", "warnings", server_default=None)
        op.alter_column("budget_estimates", "suggestions", server_default=None)

    if not _has_table(bind, "route_plans"):
        op.create_table(
            "route_plans",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("total_distance_km", sa.Float(), nullable=False),
            sa.Column("total_travel_time_minutes", sa.Float(), nullable=False),
            sa.Column("full_encoded_polyline", sa.Text(), nullable=True),
            sa.Column(
                "days",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.alter_column("route_plans", "days", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()

    if _has_column(bind, "preferences", "interests"):
        op.drop_column("preferences", "interests")

    for table_name in [
        "route_plans",
        "budget_estimates",
        "selected_hotels",
        "selected_places",
        "reviews",
        "trips",
        "preferences",
        "users",
    ]:
        if _has_table(bind, table_name):
            op.drop_table(table_name)