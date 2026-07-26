"""Add route confirmation, transport costs, and daily hotel fields."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260624_0004"
down_revision = "20260619_0003"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    route_columns = _columns("route_plans")
    if "total_transport_cost_lkr" not in route_columns:
        op.add_column("route_plans", sa.Column("total_transport_cost_lkr", sa.Float(), nullable=False, server_default="0"))
    if "route_status" not in route_columns:
        op.add_column("route_plans", sa.Column("route_status", sa.String(), nullable=False, server_default="draft"))
    if "map_provider" not in route_columns:
        op.add_column("route_plans", sa.Column("map_provider", sa.String(), nullable=True))
    if "summary" not in route_columns:
        op.add_column("route_plans", sa.Column("summary", sa.Text(), nullable=True))

    place_columns = _columns("selected_places")
    if "opening_hours" not in place_columns:
        op.add_column("selected_places", sa.Column("opening_hours", sa.String(), nullable=True))
    if "availability_warnings" not in place_columns:
        op.add_column("selected_places", sa.Column("availability_warnings", postgresql.JSONB(), nullable=False, server_default="[]"))

    hotel_columns = _columns("selected_hotels")
    if "route_plan_id" not in hotel_columns:
        op.add_column("selected_hotels", sa.Column("route_plan_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_selected_hotels_route_plan_id",
            "selected_hotels",
            "route_plans",
            ["route_plan_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "day_number" not in hotel_columns:
        op.add_column("selected_hotels", sa.Column("day_number", sa.Integer(), nullable=True))
    if "transfer_distance_km" not in hotel_columns:
        op.add_column("selected_hotels", sa.Column("transfer_distance_km", sa.Float(), nullable=False, server_default="0"))
    if "transfer_time_minutes" not in hotel_columns:
        op.add_column("selected_hotels", sa.Column("transfer_time_minutes", sa.Float(), nullable=False, server_default="0"))
    if "transfer_cost_lkr" not in hotel_columns:
        op.add_column("selected_hotels", sa.Column("transfer_cost_lkr", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    for column in ["transfer_cost_lkr", "transfer_time_minutes", "transfer_distance_km", "day_number", "route_plan_id"]:
        if column in _columns("selected_hotels"):
            if column == "route_plan_id":
                op.drop_constraint("fk_selected_hotels_route_plan_id", "selected_hotels", type_="foreignkey")
            op.drop_column("selected_hotels", column)

    for column in ["availability_warnings", "opening_hours"]:
        if column in _columns("selected_places"):
            op.drop_column("selected_places", column)

    for column in ["summary", "map_provider", "route_status", "total_transport_cost_lkr"]:
        if column in _columns("route_plans"):
            op.drop_column("route_plans", column)
