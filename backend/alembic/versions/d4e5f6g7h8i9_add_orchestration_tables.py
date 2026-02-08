"""add orchestration tables

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-02-08 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: str | None = "c3d4e5f6g7h8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- email_attachments table ---
    op.create_table(
        "email_attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inbox_message_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("ocr_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("detected_category", sa.String(50), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["inbox_message_id"], ["inbox_messages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_email_attachments_inbox_message_id",
        "email_attachments",
        ["inbox_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_email_attachments_document_id",
        "email_attachments",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_email_attachments_ocr_status",
        "email_attachments",
        ["ocr_status"],
        unique=False,
    )

    # --- drawing_analyses table ---
    op.create_table(
        "drawing_analyses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("dimensions", sa.dialects.postgresql.JSON, nullable=True),
        sa.Column("materials", sa.dialects.postgresql.JSON, nullable=True),
        sa.Column("tolerances", sa.dialects.postgresql.JSON, nullable=True),
        sa.Column("surface_treatments", sa.dialects.postgresql.JSON, nullable=True),
        sa.Column("welding_requirements", sa.dialects.postgresql.JSON, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("analysis_model", sa.String(100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index(
        "ix_drawing_analyses_document_id",
        "drawing_analyses",
        ["document_id"],
        unique=False,
    )

    # --- processing_tasks table ---
    op.create_table(
        "processing_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inbox_message_id", sa.UUID(), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("input_data", sa.dialects.postgresql.JSON, nullable=True),
        sa.Column("output_data", sa.dialects.postgresql.JSON, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["inbox_message_id"], ["inbox_messages.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_processing_tasks_stage_status",
        "processing_tasks",
        ["stage", "status"],
        unique=False,
    )
    op.create_index(
        "ix_processing_tasks_created_at",
        "processing_tasks",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_processing_tasks_inbox_message_id",
        "processing_tasks",
        ["inbox_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_processing_tasks_celery_task_id",
        "processing_tasks",
        ["celery_task_id"],
        unique=False,
    )

    # --- dead_letter_queue table ---
    op.create_table(
        "dead_letter_queue",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("original_task", sa.String(255), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSON, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_traceback", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dead_letter_queue_resolved",
        "dead_letter_queue",
        ["resolved"],
        unique=False,
    )
    op.create_index(
        "ix_dead_letter_queue_stage",
        "dead_letter_queue",
        ["stage"],
        unique=False,
    )

    # --- ALTER TABLE inbox_messages ---
    op.add_column(
        "inbox_messages",
        sa.Column("parsed_data", sa.dialects.postgresql.JSON, nullable=True),
    )
    op.add_column(
        "inbox_messages", sa.Column("thread_id", sa.String(255), nullable=True)
    )
    op.add_column(
        "inbox_messages", sa.Column("references_header", sa.Text(), nullable=True)
    )
    op.add_column(
        "inbox_messages",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "inbox_messages",
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "inbox_messages",
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "ix_inbox_messages_thread_id",
        "inbox_messages",
        ["thread_id"],
        unique=False,
    )

    # --- ALTER TABLE documents ---
    op.add_column(
        "documents", sa.Column("processing_status", sa.String(20), nullable=True)
    )
    op.add_column(
        "documents", sa.Column("source_attachment_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "documents", sa.Column("inbox_message_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "fk_documents_source_attachment_id",
        "documents",
        "email_attachments",
        ["source_attachment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_documents_inbox_message_id",
        "documents",
        "inbox_messages",
        ["inbox_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_documents_source_attachment_id",
        "documents",
        ["source_attachment_id"],
        unique=False,
    )
    op.create_index(
        "ix_documents_inbox_message_id",
        "documents",
        ["inbox_message_id"],
        unique=False,
    )


def downgrade() -> None:
    # --- ALTER TABLE documents (reverse) ---
    op.drop_index("ix_documents_inbox_message_id", table_name="documents")
    op.drop_index("ix_documents_source_attachment_id", table_name="documents")
    op.drop_constraint(
        "fk_documents_inbox_message_id", "documents", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_documents_source_attachment_id", "documents", type_="foreignkey"
    )
    op.drop_column("documents", "inbox_message_id")
    op.drop_column("documents", "source_attachment_id")
    op.drop_column("documents", "processing_status")

    # --- ALTER TABLE inbox_messages (reverse) ---
    op.drop_index("ix_inbox_messages_thread_id", table_name="inbox_messages")
    op.drop_column("inbox_messages", "needs_review")
    op.drop_column("inbox_messages", "processing_completed_at")
    op.drop_column("inbox_messages", "processing_started_at")
    op.drop_column("inbox_messages", "references_header")
    op.drop_column("inbox_messages", "thread_id")
    op.drop_column("inbox_messages", "parsed_data")

    # --- dead_letter_queue table ---
    op.drop_index("ix_dead_letter_queue_stage", table_name="dead_letter_queue")
    op.drop_index("ix_dead_letter_queue_resolved", table_name="dead_letter_queue")
    op.drop_table("dead_letter_queue")

    # --- processing_tasks table ---
    op.drop_index(
        "ix_processing_tasks_celery_task_id", table_name="processing_tasks"
    )
    op.drop_index(
        "ix_processing_tasks_inbox_message_id", table_name="processing_tasks"
    )
    op.drop_index("ix_processing_tasks_created_at", table_name="processing_tasks")
    op.drop_index("ix_processing_tasks_stage_status", table_name="processing_tasks")
    op.drop_table("processing_tasks")

    # --- drawing_analyses table ---
    op.drop_index("ix_drawing_analyses_document_id", table_name="drawing_analyses")
    op.drop_table("drawing_analyses")

    # --- email_attachments table ---
    op.drop_index("ix_email_attachments_ocr_status", table_name="email_attachments")
    op.drop_index("ix_email_attachments_document_id", table_name="email_attachments")
    op.drop_index(
        "ix_email_attachments_inbox_message_id", table_name="email_attachments"
    )
    op.drop_table("email_attachments")
