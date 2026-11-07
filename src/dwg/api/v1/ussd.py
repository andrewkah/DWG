""" USSD webhook endpoints (/v1/ussd/*)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from dwg.adapters.ussd.africas_talking import AfricasTalkingAdapter
from dwg.adapters.ussd.base import UssdProviderAdapter
from dwg.adapters.ussd.mock import MockUssdAdapter
from dwg.adapters.ussd.ussd_service import UssdChannelService
from dwg.api.schemas_and_dependencies import get_session_service, get_workflow_repository
from dwg.engine.services.session_service import SessionService
from dwg.storage.repositories.interfaces import WorkflowRepository


ussd_router = APIRouter(prefix="/ussd", tags=["USSD Webhooks"])

# Provider registry
_ADAPTERS: dict[str, UssdProviderAdapter] = {
    "mock": MockUssdAdapter(),
    "africas_talking": AfricasTalkingAdapter(),
}

# In-memory singleton UssdChannelService for development
_ussd_channel_service: UssdChannelService | None = None


def get_ussd_channel_service(
    session_service: SessionService = Depends(get_session_service),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
) -> UssdChannelService:
    global _ussd_channel_service
    if _ussd_channel_service is None:
        _ussd_channel_service = UssdChannelService(
            session_service, workflow_repo
        )
    return _ussd_channel_service


@ussd_router.post("/{provider}", response_class=Response)
async def handle_ussd_webhook(
    provider: str,
    request: Request,
    ussd_service: UssdChannelService = Depends(get_ussd_channel_service),
) -> Response:
    """Universal webhook endpoint for USSD providers (Africa's Talking, Mock, etc.)."""
    adapter = _ADAPTERS.get(provider)
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"USSD Provider '{provider}' is not supported.",
        )

    # 1. Transport parsing via adapter SPI
    canonical_req = await adapter.parse_request(request)

    # 2. Channel orchestration
    canonical_res = ussd_service.handle_turn(canonical_req)

    # 3. Provider-specific response rendering
    return adapter.render_response(canonical_res)