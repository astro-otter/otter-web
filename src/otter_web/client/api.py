"""
An API endpoint to query the database, with some protection
"""

import os
import requests
from functools import partial
from typing import Callable
from nicegui import ui, Client, run
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi import Request, APIRouter

from ..theme import frame
from ..config import API_URL, WEB_BASE_URL

from otter import Otter

API_ROUTER = APIRouter()

async def arangodb_proxy_post(request:Request, proxy_url:str):
    """
    Some general proxy code to post JSON to arangodb

    Args:
        request [Request] : the fastapi request object
        proxy_url [str] : The url to spoof
    """
    try:
        body = await request.json()
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": True, "code": 400, "errorMessage": f"Invalid JSON body: {str(e)}"}
        )

    # Send query to ArangoDB
    try:
        response = await run.io_bound(
            requests.post,
            proxy_url,
            json=body
        )
        response.raise_for_status()
    except Exception as e:
        response = JSONResponse(
            status_code=500,
            content={
                'error': True,
                "code": 500,
                "errorMessage": f'Failed to fetch data from ArangoDB through the Proxy: {e}'
            }
        )
        return response

    json_resp = JSONResponse(
        status_code=response.status_code,
        content=response.json()
    )
    return json_resp

async def arangodb_proxy_get(request:Request, proxy_url:str):
    """
    Some general proxy code to post JSON to arangodb

    Args:
        request [Request] : the fastapi request object
        proxy_url [str] : The url to spoof
    """
    try:
        body = await request.body()
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": True, "code": 400, "errorMessage": f"Invalid request body: {str(e)}"}
        )

    # Send query to ArangoDB
    try:
        response = await run.io_bound(
            requests.get,
            proxy_url
        )
        response.raise_for_status()
    except Exception as e:
        response = JSONResponse(
            status_code=500,
            content={
                'error': True,
                "code": 500,
                "errorMessage": f'Failed to fetch data from ArangoDB through the Proxy: {e}'
            }
        )
        return response

    json_resp = JSONResponse(
        status_code=response.status_code,
        content=response.json()
    )
    return json_resp

@API_ROUTER.get(os.path.join(WEB_BASE_URL, "api", "_api/user/{user}/database"))
async def api_db(user:str, request:Request):
    redirect_url = f"{API_URL}/_api/user/{user}/database"
    return await arangodb_proxy_get(request, redirect_url)
    
@API_ROUTER.get(os.path.join(WEB_BASE_URL, "api/_db/{db}/_api/collection"))
async def api_collection(db:str, request:Request):
    redirect_url = f"{API_URL}/_db/{db}/_api/collection"
    return await arangodb_proxy_get(request, redirect_url)
    
@API_ROUTER.get(os.path.join(WEB_BASE_URL, "api/_db/{db}/_api/gharial"))
async def api_gharial(db:str, request:Request):
    redirect_url = f"{API_URL}/_db/{db}/_api/gharial"
    return await arangodb_proxy_get(request, redirect_url)
    
# http://127.0.0.1:8080/api/_db/otter/_api/foxx?excludeSystem=False
@API_ROUTER.get(os.path.join(WEB_BASE_URL, "api/_db/{db}/_api/foxx"))
async def api_foxx(db: str, request: Request):
    redirect_url = f"{API_URL}/_db/{db}/_api/foxx"
    return await arangodb_proxy_get(request, redirect_url)

@API_ROUTER.post(os.path.join(WEB_BASE_URL, "api/_db/{db}/_api/cursor"))
async def api_proxy_cursor(db: str, request: Request):
    proxy_url = f"{API_URL}/_db/{db}/_api/cursor"
    arango_resp = await arangodb_proxy_post(request, proxy_url)
    return arango_resp
