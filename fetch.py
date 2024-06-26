import json
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "http://localhost:8000"
DATA_PATH = Path("data/properties.json")

# from fetch import DATA_PATH; import json; len(json.loads(DATA_PATH.read_bytes()))


def store_json_data(path: Path, data: list[dict]) -> None:
    if path.exists():
        data.extend(json.loads(path.read_bytes()))
    with path.open("w") as f:
        json.dump(data, f)


def fetch_data(
    client: httpx.Client,
    pages: tuple[int, int],
    city: str,
) -> list[dict[str, Any]]:
    response = client.post(
        f"/v1/search/city/{city}",
        params={"start": pages[0], "end": pages[1]},
    )
    if response.status_code == 200:
        return response.json()
    raise ValueError(f"Response status code: {response.status_code}")


if __name__ == "__main__":
    for page in range(11, 31, 5):
        print(f"Fetching Pages: ({page}, {page+5})")
        with httpx.Client(base_url=BASE_URL, timeout=20) as client:
            data = fetch_data(client, (page, page + 5), "gurgaon")
        store_json_data(DATA_PATH, data)
        print(f"Total data fetched: {len(data)}")
