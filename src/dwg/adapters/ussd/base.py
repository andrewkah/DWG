""" UssdProviderAdapter (Abstract SPI)
"""

from abc import ABC, abstractmethod
from fastapi import Request, Response
from enum import Enum

from pydantic import BaseModel

class USSDAction(str, Enum):
    CON = "CON" # Telco keeps session open and awaits input
    END = "END" # Telco displays message and closes connection
    
class CanonicalUSSDRequest(BaseModel):
    provider: str
    provider_session_id: str
    subscriber_id: str # E.164 phone number
    service_code: str # e.g. *122*200#
    raw_input: str # Extracted current turn input
    is_new_session: bool
    
class CanonicalUSSDResponse(BaseModel):
    action: USSDAction
    message: str
    
class UssdProviderAdapter(ABC):
    @abstractmethod
    def get_provider_name(self) -> str:
        """ Returns the unique provider slug.
        """
        pass
    
    @abstractmethod
    async def parse_request(self, request: Request) -> CanonicalUSSDRequest:
        """ Parses transport-specific webhook into CanonicalUSSDRequest.
        """
        pass
    
    @abstractmethod
    def render_response(self, request: CanonicalUSSDResponse) -> Response:
        """ formats CanonicalUSSDResponse into the provider's HTTP Payload."""
        pass
        