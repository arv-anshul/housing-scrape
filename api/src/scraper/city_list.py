import json
from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path

import curler
import httpx

CITY_LIST_CURL_PATH = Path("data/requests/city_list/requests.curl")
CITY_LIST_DATA_PATH = Path("data/requests/city_list/requests.data")

logger = getLogger(__name__)


@dataclass(kw_only=True, eq=False)
class CityList:
    curl_command: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.curl = (
            curler.parse_curl(self.curl_command)
            if self.curl_command
            else curler.parse_file(CITY_LIST_CURL_PATH)
        )
        self.json_data = json.loads(CITY_LIST_DATA_PATH.read_bytes())

    async def request(self, client: httpx.AsyncClient) -> dict:
        res = await client.post(
            self.curl.url,
            params=self.curl.params,
            json=self.json_data,
            headers=self.curl.headers,
            cookies=self.curl.cookies,
            timeout=3,
        )

        if res.status_code != 200:
            logger.error(res.text)
            raise httpx.HTTPStatusError(
                f"{self.curl.method}:{res.status_code}:{res.url}",
                request=res.request,
                response=res,
            )
        return res.json()
