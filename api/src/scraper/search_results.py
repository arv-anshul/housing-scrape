import asyncio
import json
from contextlib import suppress as suppress_error
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

import curler
import httpx

from api.errors import PaginationError
from api.models.payloads.search_results import ApiHashModel, MetaApi

SEARCH_RESULT_CURL_PATH = Path("data/requests/search_results/requests.curl")
SEARCH_RESULT_DATA_PATH = Path("data/requests/search_results/requests.data")

logger = getLogger(__name__)


@dataclass(kw_only=True, eq=False)
class SearchResults:
    start_end_page: tuple[int, int]
    size: int = 30

    def __post_init__(self) -> None:
        # Validate start_end_page argument
        if self.start_end_page[0] > self.start_end_page[1]:
            raise ValueError("First value must be larger than second value.")

        self.curl = curler.parse_file(SEARCH_RESULT_CURL_PATH)
        self.json_data = {
            "query": (
                json.loads(self.curl.data_binary.strip("$").replace("\\\\", "\\"))[  # type: ignore
                    "query"
                ].replace("\\n", " ")
            ),
            "variables": ApiHashModel.from_curl(SEARCH_RESULT_CURL_PATH).model_dump(),
        }

        # Set page size paramerter
        self.json_data["variables"]["pageInfo"]["size"] = self.size

    async def first_request(self, client: httpx.AsyncClient):
        """Make the first request to figure out requests params."""
        _data = self.json_data.copy()
        with suppress_error(KeyError):
            logger.info("Removing 'meta.api' keys for `first_request` method.")
            del _data["variables"]["meta"]["api"]
        _data["variables"] = json.dumps(_data["variables"])

        res = await client.post(
            self.curl.url,
            params=self.curl.params,
            headers=self.curl.headers,
            cookies=self.curl.cookies,
            json=_data,
            timeout=3,
        )

        if res.status_code == 200:
            response_data = res.json()
            self._update_cursor(response_data)
            self.calc_pages(response_data)
        else:
            logger.error(res.text)
            raise httpx.HTTPStatusError(
                f"{self.curl.method}:{res.status_code}:{res.url}",
                request=res.request,
                response=res,
            )

    async def request(
        self,
        client: httpx.AsyncClient,
    ) -> list[dict]:
        all_response = []
        updater = self.requests_params_updater()
        counter = 1

        await self.first_request(client)
        for _ in range(self._n_iter):
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

            if res.status_code == 200:
                response_data = res.json()
                all_response.append(
                    response_data["data"]["searchResults"]["properties"]
                )
                self._update_cursor(response_data)
            else:
                logger.error(res.text)
                logger.info("Not appending the response.")
                logger.warning(
                    "Returning all fetched resposes till page %d.",
                    self.json_data["variables"]["pageInfo"]["page"],
                )
                return all_response

            if counter == 7:
                sleep = 3
                logger.critical(f"Sleep of {sleep} seconds...")
                await asyncio.sleep(sleep)
                counter = 1
            else:
                counter += 1

        return all_response

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
        for _ in range(self._n_iter):
            [next(i) for i in all_updater]
            yield

    def calc_pages(self, data: dict):
        """
        Calculate page numbers to fetch. Also ensure the starting and ending pages.
        """
        try:
            page_info = data["data"]["searchResults"]["config"]["pageInfo"]
        except KeyError:
            logger.error("Error while getting 'pageInfo' from response data.")
            raise

        n_pages = page_info["totalCount"] // page_info["size"] + 1
        logger.info(f"Batch's pageInfo: {page_info}")
        logger.info(f"Total page for this request batch calculated as {n_pages}.")

        error_msg: str | None = None
        if n_pages < self.start_end_page[0]:
            error_msg = (
                f"You have requested more than maximum page number {n_pages}. "
                f"Requested page number must be between [1, {n_pages}]"
            )
        elif n_pages < 2:
            error_msg = (
                f"Requested city has only {page_info['totalCount']} properties. "
                "No further request should be made."
            )
        if error_msg:
            logger.error(error_msg)
            raise PaginationError(error_msg)

        self.pages = range(
            max(1, self.start_end_page[0]),
            min(n_pages, self.start_end_page[1]) + 1,
        )
        logger.info(f"Fetching pages {self.pages}.")
        self._n_iter = len(self.pages)
