import json
from functools import lru_cache
from typing import Any

from api.constants import REQUESTS_UTILS_JSON_PATH


@lru_cache(1)
def load_requests_utils() -> dict[str, Any]:
    return json.loads(REQUESTS_UTILS_JSON_PATH.read_bytes())
