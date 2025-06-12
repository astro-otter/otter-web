from typing import Optional
import glob
import os
import io
import json
from datetime import datetime
import logging
from copy import deepcopy

import pandas as pd

from ..config import vetting_password, unrestricted_page_routes, otterpath, API_URL, WEB_BASE_URL
from ..theme import frame

from otter import Otter, Transient

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from pyArango.connection import Connection
from pyArango.database import Database

from nicegui import app, ui

log = logging.getLogger("otter-log")

passwords = {"vetting-user": vetting_password}

transient_to_approve = {}

class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.

    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if 'vetting' in request.url.path:
                app.storage.user['referrer_path'] = request.url.path  # remember where the user wanted to go
                return RedirectResponse(os.path.join(WEB_BASE_URL, 'login'))
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
                "name": "approved",
                "label": "Approved?",
                "field": "approved",
                "required": True,
                "sortable": True,
                "align": "left"
            },
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
            comment = t["schema_version"]["comment"].split("|")
            name, email = comment[0:2]

            name = name.replace("Uploader:", "").strip()
            email = email.replace("Email:", "").strip()
            approved = "approved" in t["schema_version"]["comment"].lower()
            table.add_rows(
                {
                    "approved" : "Yes" if approved else "Not yet!",
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
            
        with ui.column().classes('bottom items-center'):
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

    global transient_to_approve
    transient_to_approve = t_doc.getStore()

    comments = transient_to_approve["schema_version"]["comment"].split("|")
    name, email = comments[0:2]
    name = name.replace("Uploader:", "").strip()
    email = email.replace("Email:", "").strip()

    with frame():

        ui.label(f"Dataset {dataset_id}").classes("text-h4")

        with ui.row():
            ui.button("Approve", color='green',
                      on_click=lambda:approve(t_doc))
            ui.button("Reject", color='red', on_click=lambda:reject(dataset_id, conn))
            
            ui.button(
                "Download Dataset",
                color='grey',
                on_click=lambda:download_dataset(transient_to_approve, dataset_id)
            )
        
        msg = f"""
**Instructions**
        
Please review the JSON data shown below in the editor. If you have minor edits please
switch to the "text" tab at the top left of the editor, make those changes, and click
"Save Changes" at the bottom. Use the above buttons to Approve and Deny this dataset.
If you have major changes, please contact the uploader via the information below.

**Uploader Information**

*Uploader Name*: {name}\n
*Uploader Email*: {email}

**JSON Data**        
"""

        ui.restructured_text(msg)
        editor = ui.json_editor(
            {'content': {'json': transient_to_approve}},
        ).classes('w-full')

        async def save_data():
            global transient_to_approve
            data = await editor.run_editor_method("get")
            transient_to_approve = eval(data['text'])
            ui.notify("Changes saved!")
            
        ui.button("Save Changes", on_click=save_data)
        
        
def approve(doc, testing=False):

    global transient_to_approve
    t = transient_to_approve
    tpatch = deepcopy(t)
    tpatch["schema_version"]["comment"] = t["schema_version"]["comment"] + " | approved"
    doc.set(tpatch)
    doc.patch()
    
    print(doc.getPatches())
    
    n = ui.notification("Processing the data, this may take a little...")
    n.spinner = True
    
    try:
        # this will upload the dataset to the transients collection in the arangodb
        # database
        db = Otter(
            username="vetting-user",
            password=vetting_password,
            url = API_URL
        )

        res = db.query(coords=Transient(t).get_skycoord())
        if len(res) > 1:
            raise OtterLimitationError(
                "Some objects in Otter are too close! Consider reducing the search radius!"
            )

        elif len(res) == 1:
            log.info("Match found in OTTER for this transient, merging!")
            # this object exists in otter already, let's grab the transient data and
            # merge the files

            # save and remove some keys so the merging works
            _key = res[0]["_key"]
            _id = str(res[0]["_id"])
            del res[0]["_key"]
            del res[0]["_id"]
            del res[0]["_rev"] # we don't need to save this one
            
            merged = Transient(t) + res[0]
            
            # copy over the special arangodb keys
            merged["_key"] = _key
            merged["_id"] = _id.replace("vetting", "transients")
            
            # we also have to delete the document from the OTTER database
            if not testing:
                log.debug(f"Removing old document: {_id}")
                #doc.delete()
            else:
                log.debug(f"Would delete\n{_id}")

        else:
            log.info("No match found in OTTER, uploading as a new transient!")
            # remove protected keys that will need to get updated
            del t["_id"]
            del t["_key"]
            del t["_rev"]
            
            merged = t

        doc = db.upload(merged, collection="transients", testing=testing)
        
    except Exception as e:
        ui.notify("Processing the dataset failed, please check again!", type="negative")
        ui.notify(e, type="negative")
        log.exception(e)
        return
    
    ui.navigate.to(os.path.join(WEB_BASE_URL, "vetting"))
    ui.notification("Data was successfully processed!")

    log.info(f"Successfully imported dataset: {t}")
    
def reject(dataset_id, conn):

    db = Database(conn, "otter")
    t_doc = db.fetchDocument(f"vetting/{dataset_id}")
    t_doc.delete()
    
    ui.navigate.to(os.path.join(WEB_BASE_URL, "vetting"))
    ui.notify("Rejection successful!", type="positive")

    log.info(f"Rejected dataset {dataset_id}!")
    
def download_dataset(t, dataset_id):
    ui.download(bytes(t), f"{dataset_id}.csv")
        
@ui.page(os.path.join(WEB_BASE_URL, 'login'))
def login() -> Optional[RedirectResponse]:
    def try_login() -> None:  # local function to avoid passing username and password as arguments
        if passwords.get(username.value) == password.value:
            app.storage.user.update({'username': username.value, 'authenticated': True})
            ui.navigate.to(app.storage.user.get('referrer_path', '/'))  # go back to where the user wanted to go
        else:
            ui.notify('Wrong username or password', color='negative')

    with frame():
        if app.storage.user.get('authenticated', False):
            return RedirectResponse(WEB_BASE_URL)
        with ui.card().classes('absolute-center'):
            username = ui.input('Username').on('keydown.enter', try_login)
            password = ui.input('Password', password=True, password_toggle_button=True).on('keydown.enter', try_login)
            ui.button('Log in', on_click=try_login)
        return None

