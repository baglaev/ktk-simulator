"""Store application users with Argon2 password hashes."""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "20260811_03"
down_revision = "20260811_02"
branch_labels = None
depends_on = None


INSTRUCTOR_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$Fj2jHIKx+q36hzn3zDIA1Q$"
    "6rA3gTQeGwhx7SuJRLqiC9vK4NQrqLHpkuahcmVi2o8"
)
TRAINEE_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$oUiAfh7bcLwwAfjcNkfckg$"
    "ifiPTvOzogI6M9zblb3/5rFj8N6xouAYmxpARLh1duM"
)


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "app_users" not in tables:
        op.create_table(
            "app_users",
            sa.Column("login", sa.String(128), primary_key=True),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("role", sa.String(32), nullable=False),
            sa.Column("full_name", sa.String(255), nullable=False),
            sa.Column(
                "assigned_instructor_id",
                sa.String(128),
                nullable=True,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
        )
        op.create_index("ix_app_users_role", "app_users", ["role"])
        op.create_index(
            "ix_app_users_assigned_instructor_id",
            "app_users",
            ["assigned_instructor_id"],
        )
        op.create_index(
            "ix_app_users_is_active",
            "app_users",
            ["is_active"],
        )

    users = sa.table(
        "app_users",
        sa.column("login", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("role", sa.String),
        sa.column("full_name", sa.String),
        sa.column("assigned_instructor_id", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    existing_logins = set(
        bind.execute(sa.select(users.c.login)).scalars()
    )
    created_at = datetime(2026, 8, 11, tzinfo=timezone.utc)
    seed_rows = [
        {
            "login": "Petrov.PP",
            "password_hash": INSTRUCTOR_PASSWORD_HASH,
            "role": "instructor",
            "full_name": "Петров П. П.",
            "assigned_instructor_id": None,
            "is_active": True,
            "created_at": created_at,
        },
        {
            "login": "Ivanov.II",
            "password_hash": TRAINEE_PASSWORD_HASH,
            "role": "user",
            "full_name": "Иванов И. И.",
            "assigned_instructor_id": "Petrov.PP",
            "is_active": True,
            "created_at": created_at,
        },
    ]
    rows_to_insert = [
        row for row in seed_rows if row["login"] not in existing_logins
    ]
    if rows_to_insert:
        op.bulk_insert(users, rows_to_insert)


def downgrade() -> None:
    op.drop_table("app_users")
