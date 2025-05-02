from typing import Optional
import glob
import os
import io
import json
from datetime import datetime

import pandas as pd

from ..config import vetting_password, unrestricted_page_routes, otterpath, API_URL, WEB_BASE_URL
from ..theme import frame

from otter import Otter

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from pyArango.connection import Connection
from pyArango.database import Database

from nicegui import app, ui

passwords = {"vetting-user": vetting_password}

class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.

    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if request.url.path.startswith('/vetting'):
                app.storage.user['referrer_path'] = request.url.path  # remember where the user wanted to go
                return RedirectResponse('/login')
        return await call_next(request)


app.add_middleware(AuthMiddleware)

@ui.page(os.path.join(WEB_BASE_URL, 'vetting'))
def vetting() -> None:
    def logout() -> None:
        app.storage.user.clear()
        ui.navigate.to(WEB_BASE_URL)

    with frame():

        columns = [
            {
                "name": "dataset_id",
                "label": "Dataset Unique ID",
                "field": "dataset_id",
                "required": True                
            },
            {
                "name": "uploader_name",
                "label": "Uploader Name",
                "field": "uploader_name",
                "required": True,
                "sortable": True,
                "align": "left",
            },
            {
                "name": "uploader_email",
                "label": "Uploader Email",
                "field": "uploader_email",
                "required": True,
                "sortable": True,
                "align": "left"
            },
        ]

        ui.label("Datasets to be Vetted").classes("text-h5")
        
        table = (
            ui.table(columns=columns, rows=[], row_key="id", pagination=10)
            .props("flat")
            .classes("w-full")
        )

        conn = Connection(
            username="vetting-user",
            password=vetting_password,
            arangoURL=API_URL
        )

        db = Database(conn, "otter")
        transients_to_vet = db.AQLQuery("FOR t IN vetting RETURN t")
        
        for t in transients_to_vet:
            name, email = t["schema_version"]["comment"].split("|")
            name = name.replace("Uploader:", "").strip()
            email = email.replace("Email:", "").strip()
            table.add_rows(
                {
                    "dataset_id": t["_id"],
                    "uploader_name": name,
                    "uploader_email": email,
                }
            )

        table.add_slot(
            'body-cell-title',
            r'<td><a :href="props.row.url">{{ props.row.title }}</a></td>'
        )
        table.on(
            'rowClick',
            lambda e : ui.navigate.to(
                os.path.join(
                    WEB_BASE_URL,
                    f'{e.args[1]["dataset_id"]}'
                )
            )
        )
            
        with ui.column().classes('absolute-center items-center'):
            ui.button(on_click=logout, icon='logout').props('outline round')

@ui.page(os.path.join(WEB_BASE_URL, "vetting/{dataset_id}"))
def vetting_subpage(dataset_id):

    conn = Connection(
        username="vetting-user",
        password=vetting_password,
        arangoURL=API_URL
    )

    db = Database(conn, "otter")
    t_doc = db.fetchDocument(f"vetting/{dataset_id}")
    t = t_doc.getStore()
    
    name, email = t["schema_version"]["comment"].split("|")
    name = name.replace("Uploader:", "").strip()
    email = email.replace("Email:", "").strip()
    
    with frame():

        ui.label(f"Dataset {dataset_id}").classes("text-h4")

        with ui.row():
            ui.button("Approve", color='green',
                      on_click=lambda:approve(t))
            ui.button("Reject", color='red', on_click=lambda:reject(dataset_id))
            
            ui.button(
                "Download Dataset",
                color='grey',
                on_click=lambda:download_dataset(t, dataset_id)
            )
        
        msg = f"""
**Uploader Information**

*Uploader Name*: {name}\n
*Uploader Email*: {email}

**JSON Data**        
"""
        ui.restructured_text(msg)
        ui.json_editor(
            {'content': {'json': t}}
        ).classes('w-full')

def approve(t):

    ui.notify("Processing the data, this takes a little...")
    
    try:
        # this will upload the dataset to the transients collection in the arangodb
        # database
        db = Otter(
            username="vetting-user",
            password=vetting_password,
            arangoURL = API_URL
        )
        
        db.upload(t, collection="otter")
        
    except Exception as e:
        ui.notify("Processing the dataset failed, please check again!", type="negative")
        ui.notify(e, type="negative")
        return
    
    ui.notify("Data was successfully processed!")
    ui.navigate.to(os.path.join(WEB_BASE_URL, "vetting"))
    
def reject(dataset_id):

    db = Database(conn, "otter")
    t_doc = db.fetchDocument(f"vetting/{dataset_id}")
    t_doc.delete()
    
    ui.navigate.to(os.path.join(WEB_BASE_URL, "vetting"))
    ui.notify("Rejection successful!", type="positive")
    
def download_dataset(t, dataset_id):
    ui.download(bytes(t), f"{dataset_id}.csv")
        
@ui.page(os.path.join(WEB_BASE_URL, '/login'))
def login() -> Optional[RedirectResponse]:
    def try_login() -> None:  # local function to avoid passing username and password as arguments
        if passwords.get(username.value) == password.value:
            app.storage.user.update({'username': username.value, 'authenticated': True})
            ui.navigate.to(app.storage.user.get('referrer_path', '/'))  # go back to where the user wanted to go
        else:
            ui.notify('Wrong username or password', color='negative')

    with frame():
        if app.storage.user.get('authenticated', False):
            return RedirectResponse('/')
        with ui.card().classes('absolute-center'):
            username = ui.input('Username').on('keydown.enter', try_login)
            password = ui.input('Password', password=True, password_toggle_button=True).on('keydown.enter', try_login)
            ui.button('Log in', on_click=try_login)
        return None

