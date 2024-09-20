from typing import Optional
import glob
import os
import io
from datetime import datetime

import pandas as pd

from ..config import vetting_password, unrestricted_page_routes, otterpath
from ..theme import frame

from otter import Otter

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

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

@ui.page('/vetting')
def vetting() -> None:
    def logout() -> None:
        app.storage.user.clear()
        ui.navigate.to('/')

    with frame():

        columns = [
            {
                "name": "dataset_id",
                "label": "Dataset Unique ID",
                "field": "dataset_id",
                "required": True,
                "classes": "hidden",
                "headerClasses": "hidden"
                
            },
            {
                "name": "datetime",
                "label": "Upload Date & Time (UTC)",
                "field": "datetime",
                "required": True,
                "sortable": True,
                "align": "left",
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
            {
                "name": "n_meta_rows",
                "label": "Number of Transients",
                "field": "n_meta_rows",
                "sortable": True,
                "required": True
            },
            {
                "name": "n_phot_rows",
                "label": "Number of Photometry Points",
                "field": "n_phot_rows",
                "sortable": True,
                "required": True
            },
        ]

        ui.label("Datasets to be Vetted").classes("text-h5")
        
        table = (
            ui.table(columns=columns, rows=[], row_key="id", pagination=10)
            .props("flat")
            .classes("w-full")
        )

        vetting_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        for upload_data_dir in glob.glob(os.path.join(vetting_dir, "tmp", "*")):
            if "README.md" in upload_data_dir:
                continue
            with open(os.path.join(upload_data_dir, "meta.csv"), 'r') as f:
                n_meta_lines = len(f.readlines()) - 1 # ignore the header row

            phot_path = os.path.join(upload_data_dir, "photometry.csv")
            n_phot_lines = 0
            if os.path.exists(phot_path):
                with open(phot_path, 'r') as f:
                    n_phot_lines = len(f.readlines()) - 1 # ignore the header row

            with open(os.path.join(upload_data_dir, "uploader-info.txt"), 'r') as f:
                info_lines = f.readlines()

            table.add_rows(
                {
                    "dataset_id": os.path.basename(upload_data_dir),
                    "datetime": datetime.utcfromtimestamp(
                        os.path.getmtime(upload_data_dir)
                    ),
                    "uploader_name": info_lines[0],
                    "uploader_email": info_lines[1],
                    "n_meta_rows": n_meta_lines,
                    "n_phot_rows": n_phot_lines
                }
            )

        table.add_slot(
            'body-cell-title',
            r'<td><a :href="props.row.url">{{ props.row.title }}</a></td>'
        )
        table.on('rowClick', lambda e : ui.navigate.to(f'/vetting/{e.args[1]["dataset_id"]}'))

            
        with ui.column().classes('absolute-center items-center'):
            ui.button(on_click=logout, icon='logout').props('outline round')

@ui.page("/vetting/{dataset_id}")
def vetting_subpage(dataset_id):

    root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    datapath = os.path.join(root_dir, "tmp", f"{dataset_id}")

    meta_path = os.path.join(datapath, "meta.csv")
    meta_df = pd.read_csv(meta_path, index_col=0)
    meta_str = io.StringIO()
    meta_df.to_markdown(meta_str, index=False, tablefmt="grid")
    
    phot_path = os.path.join(datapath, "photometry.csv")
    phot_df = None
    if os.path.exists(phot_path):
        phot_df = pd.read_csv(phot_path, index_col=0)
        
    phot_str = io.StringIO()
    if phot_df is not None:
        phot_df.to_markdown(phot_str, index=False, tablefmt="grid")
        
    info_path = os.path.join(datapath, "uploader-info.txt")
    with open(info_path, "r") as f:
        lines = f.readlines()

    
    with frame():

        ui.label(f"Dataset {dataset_id}").classes("text-h4")

        with ui.row():
            ui.button("Approve", color='green',
                      on_click=lambda:approve(datapath, otterpath))
            ui.button("Reject", color='red', on_click=lambda:reject(datapath))
            
            ui.button(
                "Download Dataset",
                color='grey',
                on_click=lambda:download_dataset(dataset_id, meta_df, phot_df)
            )
        
        msg = f"""
**Uploader Information**

*Uploader Name*: {lines[0]}
*Uploader Email*: {lines[1]}

**Metadata**

{meta_str.getvalue()}

**Photometry**

{phot_str.getvalue()}

"""
        ui.restructured_text(msg)

def approve(indatapath, otterpath):

    ui.notify("Processing the data, this takes a little...")
    
    metapath = os.path.join(indatapath, "meta.csv")
    photpath = os.path.join(indatapath, "photometry.csv")
    if not os.path.exists(photpath):
        photpath = None
    
    unprocessed_data_path = os.path.join(otterpath, "unprocessed-data", "uploaded-data")
    processed_data_path = os.path.join(otterpath, ".otter")

    try:
        # this will write/merge the meta and photometry files to the .otter directory
        # THIS MEANS IT WILL ONLY BE STORED LOCALLY UNTIL THE DATABASE IS REFRESHED!!!
        new_db = Otter.from_csvs(metapath, photpath, processed_data_path)
        
    except Exception as e:
        ui.notify("Processing the dataset failed, please check again!", type="negative")
        ui.notify(e, type="negative")
        return
    
    # then move the files to the unprocessed-data directory
    dirname = os.path.dirname(metapath)
    dataset_id = basename(dirname)
    os.rename(dirname, os.path.join(unprocessed_data_path, dataset_id))    

    ui.notify("Data was successfully processed!")
    ui.navigate.to("/vetting")
    
def reject(datapath):

    for file in glob.glob(os.path.join(datapath, '*')):
        os.remove(file)

    os.rmdir(datapath)

    ui.navigate.to("/vetting")
    ui.notify("Rejection successful!", type="positive")
    
def download_dataset(dataset_id, meta_df, phot_df=None):

    meta_bytes = bytes(
        meta_df.to_csv(index=False),
        encoding='utf-8'
    )
    ui.download(meta_bytes, f"meta-{dataset_id}.csv")

    if phot_df is not None:
        phot_bytes = bytes(
            phot_df.to_csv(index=False),
            encoding='utf-8'
        )
        ui.download(phot_bytes, f"phot-{dataset_id}.csv")
    
@ui.page('/login')
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

