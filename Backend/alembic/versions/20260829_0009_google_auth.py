"""Add Google account authentication fields."""

import sqlalchemy as sa

from alembic import op

revision = "20260829_0009"
down_revision = "20260802_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(),
        nullable=True,
    )
    op.add_column("users", sa.Column("google_subject", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_google_subject", "users", ["google_subject"])


def downgrade() -> None:
    oauth_only_accounts = sa.table(
        "users",
        sa.column("password_hash", sa.String()),
    )
    op.execute(
        oauth_only_accounts.update()
        .where(oauth_only_accounts.c.password_hash.is_(None))
        .values(password_hash="$2b$12$Qq6N8ycb4N3rhJ1F/PZp2u7jZqY6oYpiKdawZfUWOUpv4YHjQ2q8G")
    )
    op.drop_constraint("uq_users_google_subject", "users", type_="unique")
    op.drop_column("users", "google_subject")
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(),
        nullable=False,
    )
