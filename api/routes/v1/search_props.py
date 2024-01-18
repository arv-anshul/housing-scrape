import httpx
from fastapi import APIRouter, Body, HTTPException

from api.src.scraper.search_results import SearchResults

router = APIRouter(
    tags=[
        "search_props",
    ],
)


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
):
    if start > end:
        raise HTTPException(
            400,
            {
                "error": "start must be lesser than end.",
                "params": {"start": start, "end": end},
            },
        )

    scrapper = SearchResults(start_end_page=(start, end), curl_command=curl_command)
    async with httpx.AsyncClient() as client:
        all_response = await scrapper.request(client=client)
        return [j for i in all_response for j in i]
