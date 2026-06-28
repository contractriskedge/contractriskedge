"""Add UNIQUE(tenant_id, correlation_id) to workflow_instances.

Prevents duplicate workflow instances per review per tenant,
closing the TOCTOU race window described in the architectural
verification report (sprint33_phase2_architectural_verification_report.md).

Revision ID: z0a1b2c3d4e5
Revises: m0n1o2p3q4r5
Create Date: 2026-06-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "z0a1b2c3d4e5"
down_revision: Union[str, None] = "m0n1o2p3q4r5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove the old non-unique index on correlation_id
    op.drop_index("idx_workflow_instances_correlation", table_name="workflow_instances")

    # Add unique constraint — this is the primary defense against
    # duplicate workflow instances for the same review (correlation_id).
    # Tenant isolation is preserved by the composite unique key.
    op.create_unique_constraint(
        "uq_workflow_instances_tenant_correlation",
        "workflow_instances",
        ["tenant_id", "correlation_id"],
    )

    # Keep a non-unique index on correlation_id alone for other lookups
    op.create_index(
        "ix_workflow_instances_correlation_id",
        "workflow_instances",
        ["correlation_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_workflow_instances_tenant_correlation",
        "workflow_instances",
        type_="unique",
    )
    op.drop_index("ix_workflow_instances_correlation_id", table_name="workflow_instances")
    op.create_index(
        "idx_workflow_instances_correlation",
        "workflow_instances",
        ["correlation_id"],
    )
