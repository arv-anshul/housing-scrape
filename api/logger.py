from datetime import datetime
from functools import lru_cache
from logging import FileHandler, NullHandler, StreamHandler, basicConfig
from pathlib import Path


@lru_cache(1)
def load_logging(
    level: int,
    *,
    folder: str = "logs",
    stream_log: bool = False,
) -> None:
    log_file_path = folder / Path(f"{datetime.now():%d%m%y-%H%M}.log")
    if not log_file_path.exists():
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

    basicConfig(
        format="[%(asctime)s]:%(lineno)s:%(name)s:%(levelname)s>  %(message)s",
        level=level,
        handlers=[
            StreamHandler() if stream_log else NullHandler(),
            FileHandler(log_file_path),
        ],
    )
