import json
from abc import ABC, abstractmethod
from asyncio import sleep as asleep
from contextlib import suppress
from dataclasses import dataclass, field
from itertools import chain
from logging import getLogger
from pathlib import Path
from typing import Any

import curler
import httpx
from bs4 import BeautifulSoup

from api.errors import PaginationError, ParsingError, ScrapperError
from api.models.payloads.search_results import ApiHashModel, MetaApi
from api.utils import load_requests_utils

SEARCH_RESULT_CURL_PATH = Path("data/requests/search_results/requests.curl")
SEARCH_RESULT_DATA_PATH = Path("data/requests/search_results/requests.data")

logger = getLogger(__name__)


@dataclass(eq=False)
class SearchResultsStrategy(ABC):
    start_end_page: tuple[int, int]
    curl_command: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        # Validate start_end_page argument
        if self.start_end_page[0] < 1:
            raise ScrapperError("Starting page number must be >=1.")
        if self.start_end_page[0] > self.start_end_page[1]:
            raise ScrapperError("First value must be larger than second value.")

        self.curl = (
            curler.parse_curl(self.curl_command)
            if self.curl_command
            else curler.parse_file(SEARCH_RESULT_CURL_PATH)
        )
        self.json_data = {
            "query": json.loads(SEARCH_RESULT_DATA_PATH.read_bytes())["query"],
            "variables": ApiHashModel.from_curl(SEARCH_RESULT_CURL_PATH).model_dump(),
        }

    @abstractmethod
    async def infer_request_data(self) -> None:
        """Infer requests params to make requests for results."""

    async def request(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        all_response = []
        updater = self.requests_params_updater()
        counter = 1

        await self.infer_request_data()
        for _ in self.pages:
            # Stringify the json data
            _data = self.json_data.copy()
            _data["variables"] = json.dumps(_data["variables"])

            next(updater)
            res = await client.post(
                self.curl.url,
                params=self.curl.params,
                headers=self.curl.headers,
                cookies=self.curl.cookies,
                json=_data,
                timeout=3,
            )

            if res.status_code != 200:
                logger.error(res.text)
                logger.info("Not appending the response.")
                logger.warning(
                    "Returning all fetched resposes till page %d.",
                    self.json_data["variables"]["pageInfo"]["page"],
                )
                return all_response

            response_data = res.json()
            all_response.append(response_data["data"]["searchResults"]["properties"])
            self._update_cursor(response_data)

            if counter == 7:
                sleep = 3
                logger.critical(f"Sleep of {sleep} seconds...")
                await asleep(sleep)
                counter = 1
            else:
                counter += 1

        return list(chain(*all_response))

    def _update_cursor(self, data: dict):
        try:
            meta_api = MetaApi(**data["data"]["searchResults"]["meta"]["api"])
        except KeyError as e:
            logger.error(f"Key {e!r} not found in response's data.")
            raise
        except TypeError:
            print(data)
            raise
        # Update json data with response's data
        self.json_data["variables"]["meta"]["api"] = meta_api.model_dump()

    def _update_page(self):
        """Update page number for requests on every iteration like a generator."""
        for i in self.pages:
            logger.info(f"Updating request's page number to {i}.")
            self.json_data["variables"]["pageInfo"]["page"] = i
            yield

    def requests_params_updater(self):
        """
        Updater for response it update page number, cursor position params of requests.
        """
        all_updater = (self._update_page(),)
        for _ in self.pages:
            [next(i) for i in all_updater]
            yield

    def infer_pagination(self, total_count: int):
        """
        Infer page numbers to fetch. Also ensure the starting and ending pages.
        """
        n_pages = total_count // 30 + 1  # 30 is (default) page size
        logger.info(f"Batch's total item count: {total_count}")
        logger.info(f"Total page for this request batch calculated as {n_pages}.")

        error_msg: str | None = None
        if n_pages < self.start_end_page[0]:
            error_msg = (
                f"You have requested more than maximum page number {n_pages}. "
                f"Requested page number must be between [1, {n_pages}]"
            )
        if error_msg:
            logger.error(error_msg)
            raise PaginationError(error_msg)

        self.pages = range(
            max(1, self.start_end_page[0]),
            min(n_pages, self.start_end_page[1]) + 1,
        )
        logger.info(f"Fetching pages {self.pages}.")


@dataclass(eq=False)
class SearchResultsWithCurl(SearchResultsStrategy):
    """Search results on housing.com with curl command."""

    async def infer_request_data(self) -> None:
        """Make the first request to figure out requests params."""
        _data = self.json_data.copy()
        with suppress(KeyError):
            logger.info("Removing 'meta.api' keys for `first_request` method.")
            del _data["variables"]["meta"]["api"]
        _data["variables"] = json.dumps(_data["variables"])

        res = httpx.post(
            self.curl.url,
            params=self.curl.params,
            headers=self.curl.headers,
            cookies=self.curl.cookies,
            json=_data,
            timeout=3,
        )

        if res.status_code != 200:
            logger.error(res.text)
            raise httpx.HTTPStatusError(
                f"{self.curl.method}:{res.status_code}:{res.url}",
                request=res.request,
                response=res,
            )
        res_data = res.json()
        self._update_cursor(res_data)
        try:
            self.infer_pagination(
                res_data["data"]["searchResults"]["config"]["pageInfo"]["totalCount"]
            )
        except KeyError:
            logger.error("Error while getting 'pageInfo' from response data.")
            raise


@dataclass(kw_only=True, eq=False)
class SearchResultsWithCity(SearchResultsStrategy):
    city: str
    curl_command: None = field(default=None, init=False, repr=False)

    def __parse_html(self, html: bytes) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        main_script = soup.select_one("#initialState")
        if not main_script:
            raise ParsingError(f"Script tag not found for city {self.city!r}.")
        try:
            return json.loads(json.loads(main_script.text[36:-2]))
        except json.JSONDecodeError as e:
            raise ParsingError(
                "Error while parsing html's #initialState script."
            ) from e

    async def infer_request_data(self) -> None:
        url = f"https://www.housing.com/in/buy/{self.city}/{self.city}"

        requests_data = load_requests_utils()
        res = httpx.get(
            url=url,
            headers=requests_data["headers"],
            follow_redirects=True,
            timeout=3,
        )

        if res.status_code != 200:
            logger.error(res.text)
            raise httpx.HTTPStatusError(
                f"{self.curl.method}:{res.status_code}:{res.url}",
                request=res.request,
                response=res,
            )

        res_data = self.__parse_html(res.content)
        try:
            self.infer_pagination(res_data["filters"]["pageInfo"]["totalCount"])
        except KeyError:
            logger.error("Error while getting 'pageInfo' from response data.")
            raise

        # Set json_data for future responses
        self.json_data["variables"] = ApiHashModel.from_dict(res_data).model_dump()
