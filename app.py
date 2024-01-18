import logging
from ast import literal_eval
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from httpx import HTTPStatusError

from api.errors import ScrapperError
from api.logger import load_logging
from api.routes.v1 import city_list, search_props


@asynccontextmanager
async def main_app_lifespan(app: FastAPI):
    load_logging(level=20)
    yield


app = FastAPI(lifespan=main_app_lifespan)


@app.middleware("handle_exception")
async def handle_exception(request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logging.exception(e)
        if isinstance(e, HTTPException):
            return JSONResponse(e.detail, e.status_code, e.headers)
        if isinstance(e, ScrapperError | HTTPStatusError):
            try:
                message = literal_eval(str(e))
            except (ValueError, SyntaxError):
                message = str(e)
            return JSONResponse({"error": message, "errorType": type(e).__name__}, 400)
        raise


@app.get("/")
def root():
    return {
        "message": "Made by @arv-anshul",
        "description": "Fetch data from housing.com",
    }


app.include_router(search_props.router, prefix="/v1/search")
app.include_router(city_list.router, prefix="/v1/cityList")
