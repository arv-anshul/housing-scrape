import httpx
from fastapi import APIRouter, Body

from api.src.scraper.city_list import CityList

router = APIRouter(
    tags=[
        "city_list",
    ],
)


@router.post(
    "/curl",
    description="All the cities listed on housing.com.",
)
async def scrape_using_curl(
    curl_command: str = Body(
        description="Curl command using which api will get the data from housing.com.",
        media_type="text/plain; charset=utf-8",
    ),
):
    scrapper = CityList(curl_command=curl_command)
    async with httpx.AsyncClient() as client:
        res = await scrapper.request(client=client)
        return res
