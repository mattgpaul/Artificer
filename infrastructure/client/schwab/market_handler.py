from dataclasses import dataclass
import uuid
from infrastructure.client.schwab.schwab_client import SchwabClient
from infrastructure.logging.logger import get_logger

@dataclass
class RequestPayload:
    url: str = "https://api/schwabapi.com/marketdata/v1"
    method: str
    headers: dict
    params: dict
    data: dict
    timeout: int
    verify: bool
    uuid: str

class MarketHandler:
    def __init__(self, client: SchwabClient):
        self.client = client
        self.logger = get_logger(self.__class__.__name__)

    def _santize_payload(self, payload: RequestPayload) -> str:
        pass

    def get_market_data(self, ticker: str) -> RequestPayload:
        return RequestPayload(
            url=url + "/marketdata/v1/quotes",
            method="GET",
            headers={},
            params={},
            data={},
            timeout=10,
            verify=True,
            uuid=str(uuid.uuid4())
        )