from typing import Any

import httpx
from fastapi import APIRouter, Body, HTTPException

from api.errors import ParsingError
from api.src.scraper.search_results import (
    SearchResultsStrategy,
    SearchResultsWithCity,
    SearchResultsWithCurl,
)

router = APIRouter(
    tags=[
        "search_props",
    ],
)


async def scrape_results(
    scrapper: SearchResultsStrategy,
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        all_response = await scrapper.request(client=client)
        return all_response


@router.post(
    "/curl",
    description="Get properties from housing.com using curl command.",
)
async def scrape_using_curl(
    start: int,
    end: int,
    curl_command: str = Body(
        description="Curl command using which api will get the data from housing.com.",
        media_type="text/plain; charset=utf-8",
    ),
) -> list[dict[str, Any]]:
    scrapper = SearchResultsWithCurl(
        start_end_page=(start, end),
        curl_command=curl_command,
    )
    return await scrape_results(scrapper)


@router.post(
    "/city/{city}",
    description="Get properties from housing.com using curl command.",
)
async def scrape_using_city(
    start: int,
    end: int,
    city: str,
) -> list[dict[str, Any]]:
    scrapper = SearchResultsWithCity(
        start_end_page=(start, end),
        city=city,
    )
    try:
        return await scrape_results(scrapper)
    except (ParsingError, httpx.HTTPStatusError) as e:
        raise HTTPException(
            404,
            {
                "error": str(e),
                "errorType": type(e).__name__,
                "checkUrl": f"https://www.housing.com/in/buy/{city}/{city}",
            },
        ) from e
