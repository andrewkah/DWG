"""V1 API Router aggregator"""

from fastapi import APIRouter, Depends, status

from dwg.api.schemas_and_dependencies import (
    RegisterDevWorkflowRequest,
    get_workflow_repository,
)
from dwg.storage.repositories.interfaces import WorkflowRepository

# Dev-Only Router
dev_router = APIRouter(prefix="/dev", tags=["Development Only"])


@dev_router.post("/workflows", status_code=status.HTTP_201_CREATED)
def register_workflow_definition(
    body: RegisterDevWorkflowRequest,
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
):
    """Dev-only endpoint to register a workflow definition in the in-memory repository."""
    workflow_repo.save_version(body.version_id, body.definition)
    return {
        "version_id": body.version_id,
        "message": "Workflow definition registered successfully in memory.",
    }
