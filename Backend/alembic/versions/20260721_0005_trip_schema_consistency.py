"""Align trip constraints and timestamps with the application model."""

from alembic import op
import sqlalchemy as sa


revision = "20260721_0005"
down_revision = "20260624_0004"
branch_labels = None
depends_on = None


def _columns() -> dict[str, dict]:
    return {
        column["name"]: column
        for column in sa.inspect(op.get_bind()).get_columns("trips")
    }


def upgrade() -> None:
    columns = _columns()

    if "updated_at" not in columns:
        op.add_column(
            "trips",
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    repairs = {
        "travelers": (1, sa.Integer()),
        "transport_type": ("car", sa.String()),
        "trip_status": ("draft", sa.String()),
        "created_at": (sa.func.now(), sa.DateTime()),
    }
    for column_name, (fallback, column_type) in repairs.items():
        if column_name not in columns:
            continue
        table = sa.table("trips", sa.column(column_name, column_type))
        op.execute(
            table.update()
            .where(table.c[column_name].is_(None))
            .values({column_name: fallback})
        )
        if columns[column_name]["nullable"]:
            op.alter_column(
                "trips",
                column_name,
                existing_type=column_type,
                nullable=False,
            )

    foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys("trips")
    user_foreign_key = next(
        (
            foreign_key
            for foreign_key in foreign_keys
            if foreign_key["constrained_columns"] == ["user_id"]
        ),
        None,
    )
    on_delete = (user_foreign_key or {}).get("options", {}).get("ondelete")
    if user_foreign_key and str(on_delete).upper() != "CASCADE":
        if user_foreign_key.get("name"):
            op.drop_constraint(
                user_foreign_key["name"],
                "trips",
                type_="foreignkey",
            )
        op.create_foreign_key(
            "fk_trips_user_id_users",
            "trips",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    columns = _columns()
    for column_name, column_type in [
        ("created_at", sa.DateTime()),
        ("trip_status", sa.String()),
        ("transport_type", sa.String()),
        ("travelers", sa.Integer()),
    ]:
        if column_name in columns:
            op.alter_column(
                "trips",
                column_name,
                existing_type=column_type,
                nullable=True,
            )

    if "updated_at" in columns:
        op.drop_column("trips", "updated_at")
