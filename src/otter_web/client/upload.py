import io
import zipfile
import json

from nicegui import ui
from ..theme import frame
from ..config import API_URL
from .home import post_table

from functools import partialmethod, partial
from dataclasses import dataclass

from astropy.coordinates import SkyCoord

from otter import Otter

db = Otter(url=API_URL)

def single_object_upload_form():

    ui.input("Some question")

def multi_object_upload_form():

    ui.input("Another question")

# Function to switch between forms
def show_form(selected_form, containers=None):
    if containers is not None:
        for val in list(containers)[1:]:
            val.delete()
    if selected_form == 'Single Object':
        single_object_upload_form()
    elif selected_form == 'Multiple Objects':
        multi_object_upload_form()
        
@ui.page("/upload")
async def upload():

    partial_show_form = partial(show_form)
    
    with frame():

        ui.label("Upload Data to OTTER").classes("col-span-5 text-h4")
            
        # Display the initial
        with ui.grid(rows="auto auto").classes("w-full") as grid:
            selected_tab = ui.toggle(
                ['Single Object', 'Multiple Objects'],
                value='Single Object',
                on_change=lambda e: partial_show_form(e.value, containers=grid)
            ).style("width: 26.25%")
            
            partial_show_form(selected_tab.value)
