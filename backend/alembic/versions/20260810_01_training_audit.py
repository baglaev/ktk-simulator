"""Create training session audit tables."""

from alembic import op
import sqlalchemy as sa

revision = "20260810_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "training_sessions" not in tables:
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
    else:
        _upgrade_legacy_training_sessions(bind)

    if "operator_actions" not in tables:
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

    if "session_results" not in tables:
        op.create_table(
            "session_results",
            sa.Column("session_id", sa.String(36), primary_key=True),
            sa.Column("outcome", sa.String(32), nullable=False),
            sa.Column("total_score", sa.Integer(), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        )

    _create_missing_indexes(bind)


def downgrade() -> None:
    op.drop_table("session_results")
    op.drop_table("operator_actions")
    op.drop_table("training_sessions")


def _upgrade_legacy_training_sessions(bind) -> None:
    columns = {
        item["name"]
        for item in sa.inspect(bind).get_columns("training_sessions")
    }
    added_columns: list[str] = []
    if "model_id" not in columns:
        op.add_column(
            "training_sessions",
            sa.Column("model_id", sa.String(128), nullable=True),
        )
        op.execute(
            sa.text(
                "UPDATE training_sessions "
                "SET model_id = 'legacy-unversioned-model' "
                "WHERE model_id IS NULL"
            )
        )
        added_columns.append("model_id")
    if "model_version" not in columns:
        op.add_column(
            "training_sessions",
            sa.Column("model_version", sa.String(32), nullable=True),
        )
        op.execute(
            sa.text(
                "UPDATE training_sessions "
                "SET model_version = 'legacy' "
                "WHERE model_version IS NULL"
            )
        )
        added_columns.append("model_version")

    if added_columns:
        with op.batch_alter_table("training_sessions") as batch:
            for column_name in added_columns:
                length = 128 if column_name == "model_id" else 32
                batch.alter_column(
                    column_name,
                    existing_type=sa.String(length),
                    nullable=False,
                )


def _create_missing_indexes(bind) -> None:
    indexes = (
        ("ix_training_sessions_scenario_id", "training_sessions", ["scenario_id"]),
        ("ix_training_sessions_trainee_id", "training_sessions", ["trainee_id"]),
        ("ix_training_sessions_status", "training_sessions", ["status"]),
        ("ix_operator_actions_session_id", "operator_actions", ["session_id"]),
        ("ix_operator_actions_virtual_time_ms", "operator_actions", ["virtual_time_ms"]),
        ("ix_operator_actions_action_type", "operator_actions", ["action_type"]),
        ("ix_session_results_outcome", "session_results", ["outcome"]),
    )
    inspector = sa.inspect(bind)
    existing = {
        item["name"]
        for table_name in ("training_sessions", "operator_actions", "session_results")
        for item in inspector.get_indexes(table_name)
    }
    for name, table_name, columns in indexes:
        if name not in existing:
            op.create_index(name, table_name, columns, unique=False)
