"""Add live hint and post-session AI audit tables."""

from alembic import op
import sqlalchemy as sa

revision = "20260811_02"
down_revision = "20260810_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "issued_hints" not in tables:
        op.create_table(
            "issued_hints",
            sa.Column("hint_record_id", sa.String(80), primary_key=True),
            sa.Column("session_id", sa.String(36), nullable=False),
            sa.Column("hint_id", sa.String(128), nullable=False),
            sa.Column("virtual_time_ms", sa.Integer(), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
        )
        op.create_index("ix_issued_hints_session_id", "issued_hints", ["session_id"])
        op.create_index("ix_issued_hints_hint_id", "issued_hints", ["hint_id"])
    if "session_ai_analyses" not in tables:
        op.create_table(
            "session_ai_analyses",
            sa.Column("session_id", sa.String(36), primary_key=True),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("session_ai_analyses")
    op.drop_table("issued_hints")
