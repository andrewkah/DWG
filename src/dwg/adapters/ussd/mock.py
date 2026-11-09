from fastapi import Request, Response

from dwg.adapters.ussd.base import (
    CanonicalUSSDRequest,
    CanonicalUSSDResponse,
    USSDAction,
    UssdProviderAdapter,
)


class MockUssdAdapter(UssdProviderAdapter):
    def get_provider_name(self) -> str:
        return "mock"

    async def parse_request(self, request: Request) -> CanonicalUSSDRequest:
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            data = await request.json()
        else:
            form = await request.form()
            data = dict(form)

        provider_session_id = str(data.get("session_id", "sim-default-session"))
        subscriber_id = str(data.get("phone_number", "+256707483657"))
        service_code = str(data.get("service_code", "*234"))
        text = str(data.get("text", "")).strip()
        is_new = data.get("is_new") is True or text == "" or data.get("is_new") == "true"
        return CanonicalUSSDRequest(
            provider="mock",
            provider_session_id=provider_session_id,
            subscriber_id=subscriber_id,
            service_code=service_code,
            raw_input=text,
            is_new_session=is_new,
        )

    def render_response(self, response: CanonicalUSSDResponse) -> Response:
        # Standard GSM plain-text response: "CON <prompt>" or "END <prompt>"
        prefix = "CON " if response.action == USSDAction.CON else "END "
        return Response(content=f"{prefix}{response.message}", media_type="text/plain")
