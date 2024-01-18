"""
For Reference
-------------

```json
{
    "hash": "23sfd8fe234",
    "service": "buy",
    "category": "residential",
    "city": {
        "name": "Mumbai",
        "id": "6aa29ff8141a531ef43f",
        "cityId": "493281cb0c8550099e6b",
        "url": "mumbai",
        "isTierTwo": true,
        "products": ["paying_guest", "buy", "plots", "commercial", "rent"]
    },
    "pageInfo": { "page": 3, "size": 30 },
    "meta": {
        "filterMeta": {},
        "url": "/in/buy/searches/23ws23afd",
        "shouldModifySearchResults": true,
        "pagination_flow": false,
        "enableExperimentalFlag": false,
        "api": {
            "cursor": "1508424527",
            "np_total_count": 445,
            "np_offset": 0,
            "resale_offset": 0,
            "resale_total_count": 410
        }
    },
    "bot": false,
    "adReq": false,
    "fltcnt": "",
    "isRent": false,
    "isLandmarkSearchActive": true,
    "addSellersData": true,
    "interestLedFilter": ""
}
```
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Self

import curler
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from pathlib import Path


class City(BaseModel):
    name: str
    id: str
    cityId: str
    url: str
    isTierTwo: bool
    products: list[str] = ["paying_guest", "buy", "plots", "commercial", "rent"]


class PageInfo(BaseModel):
    page: int
    size: int


class MetaApi(BaseModel):
    cursor: str = "52596131"
    np_total_count: int = 131
    np_offset: int = 0
    resale_offset: int = 0
    resale_total_count: int = 33


class Meta(BaseModel):
    filterMeta: dict[str, Any] = Field(default_factory=dict)
    url: str
    shouldModifySearchResults: bool = True
    pagination_flow: bool = False
    enableExperimentalFlag: bool = False
    api: MetaApi = Field(default_factory=MetaApi)


class ApiHashModel(BaseModel):
    hash: str
    service: str = "buy"
    category: str = "residential"
    city: City
    pageInfo: PageInfo
    meta: Meta
    bot: bool = False
    adReq: bool = False
    fltcnt: str = ""
    isRent: bool = False
    isLandmarkSearchActive: bool = False
    addSellersData: bool = True
    interestLedFilter: str = ""

    @classmethod
    def from_curl(cls, path: Path) -> Self:
        data_raw = curler.parse_file(path).data_binary
        if not data_raw:
            raise ValueError("curl command not contains '--data-raw' argument.")
        data_raw = data_raw.strip("$")

        try:
            data = json.loads(json.loads(data_raw.replace("\\\\", "\\"))["variables"])
        except json.JSONDecodeError as e:
            e.add_note(f"Reading '{path}'")
            raise
        return cls(**data)

    @classmethod
    def generate_new_api_hash(
        cls,
        hash: str,
        *,
        city: City,
        page_info: PageInfo,
        meta: Meta,
        model_kw: dict[str, Any] | None = None,
    ) -> Self:
        return cls(
            hash=hash,
            city=city,
            pageInfo=page_info,
            meta=meta,
            **model_kw if model_kw else {},
        )
