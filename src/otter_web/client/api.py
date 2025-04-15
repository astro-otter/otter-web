"""
An API endpoint to query the database, with some protection
"""

import os
import requests
from nicegui import ui, Client, run
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi import Request, APIRouter

from ..theme import frame
from ..config import API_URL, WEB_BASE_URL

from otter import Otter

API_ROUTER = APIRouter()

@ui.page(os.path.join(WEB_BASE_URL, "api", "_api/user/{user}/database"))
async def api_db(user):
    redirect_url = f"{API_URL}/_api/user/{user}/database"
    print(redirect_url)
    return RedirectResponse(redirect_url)

@ui.page(os.path.join(WEB_BASE_URL, "api/_db/otter/_api/collection"))
async def api_collection():
    redirect_url = f"{API_URL}/_db/otter/_api/collection"
    print(redirect_url)
    return RedirectResponse(redirect_url)

@ui.page(os.path.join(WEB_BASE_URL, "api/_db/otter/_api/gharial"))
async def api_gharial():
    redirect_url = f"{API_URL}/_db/otter/_api/gharial"
    print(redirect_url)
    return RedirectResponse(redirect_url)

# http://127.0.0.1:8080/api/_db/otter/_api/foxx?excludeSystem=False
@ui.page(os.path.join(WEB_BASE_URL, "api/_db/otter/_api/foxx")) # ?excludeSystem=False
async def api_foxx():
    redirect_url = f"{API_URL}/_db/otter/_api/foxx?excludeSystem=False"
    print(redirect_url)
    return RedirectResponse(redirect_url)

@API_ROUTER.post(os.path.join(WEB_BASE_URL, "api/_db/{db}/_api/cursor"))
async def api_proxy_cursor(db: str, request: Request):
    proxy_url = f"{API_URL}/_db/otter/_api/cursor"

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
        
    # return the result
    json_resp = JSONResponse(
        status_code=response.status_code,
        content=response.json()
    )
    return json_resp 
