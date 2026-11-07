"""Africa's Talking webhook adapter"""

from fastapi import HTTPException, Request, Response, status

from dwg.adapters.ussd.base import (
    CanonicalUSSDRequest,
    CanonicalUSSDResponse,
    USSDAction,
    UssdProviderAdapter,
)


class AfricasTalkingAdapter(UssdProviderAdapter):
    def get_provider_name(self) -> str:
        return "africas_talking"

    async def parse_request(self, request: Request) -> CanonicalUSSDRequest:
        try:
            form = await request.form()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expected form-urlencoded payload from Africa's Talking",
            )

        session_id = form.get("sessionId")
        phone_number = form.get("phoneNumber")
        service_code = form.get("serviceCode")
        raw_text = form.get("text", "")

        if not session_id or not phone_number or not service_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing mandatory Africa's Talking parameters (sessionId, phoneNumber, serviceCode)",
            )

        # Africa's Talking turn history extraction:
        # e.g., "Sarah*25*1" -> current turn input is "1"
        raw_text_str = str(raw_text).strip()
        if not raw_text_str:
            current_input = ""
            is_new = True
        else:
            tokens = raw_text_str.split("*")
            current_input = tokens[-1]
            is_new = False

        return CanonicalUSSDRequest(
            provider="africas_talking",
            provider_session_id=str(session_id),
            subscriber_id=str(phone_number),
            service_code=str(service_code),
            raw_input=current_input,
            is_new_session=is_new,
        )

    def render_response(self, response: CanonicalUSSDResponse) -> Response:
        prefix = "CON " if response.action == USSDAction.CON else "END "
        return Response(content=f"{prefix}{response.message}", media_type="text/plain")
