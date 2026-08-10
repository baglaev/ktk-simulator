"""Create training session audit tables."""

from alembic import op
import sqlalchemy as sa

revision = "20260810_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_sessions",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("scenario_id", sa.String(128), nullable=False),
        sa.Column("scenario_version", sa.String(32), nullable=False),
        sa.Column("model_id", sa.String(128), nullable=False),
        sa.Column("model_version", sa.String(32), nullable=False),
        sa.Column("trainee_id", sa.String(128), nullable=False),
        sa.Column("instructor_id", sa.String(128), nullable=True),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("elapsed_time_ms", sa.Integer(), nullable=False),
        sa.Column("total_duration_ms", sa.Integer(), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "operator_actions",
        sa.Column("action_id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("virtual_time_ms", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(128), nullable=True),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("error_codes_json", sa.JSON(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "session_results",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("session_results")
    op.drop_table("operator_actions")
    op.drop_table("training_sessions")
