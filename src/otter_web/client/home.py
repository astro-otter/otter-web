import pandas as pd
from nicegui import ui
from typing import List
import datetime

from plotly import graph_objects as go
from plotly.subplots import make_subplots
from functools import partial

from ..theme import frame
from ..config import API_URL, WEB_BASE_URL

from .transient_pages import *
from .search_util import SearchResults, simple_form, _post_table

from otter import Otter, Transient

from astropy.coordinates import SkyCoord
from astropy import coordinates as coord
from astropy.time import Time
from astropy import units as u

import logging
logger = logging.getLogger("otter-log")

logger.info(API_URL)
logger.info(f"Opening API server on {API_URL}...")

@ui.page(f"{WEB_BASE_URL}")
async def page():

    @ui.refreshable
    def post_table(*args, **kwargs):
        _post_table(*args, **kwargs)
    
    search_results = SearchResults(None)

    partial_show_form = partial(
        simple_form,
        search_results=search_results,
        post_table=post_table
    )

    with frame():
        imsize=32
        with ui.grid(rows=1, columns=16).classes("gap-0 no-wrap"):

            ui.image(
                "src/otter_web/static/logo.png"
            ).classes(f"w-{imsize} col-span-4")
            
            ui.label(
                "The Open mulTiwavelength Transient Event Repository"
            ).classes("text-h2 col-span-12")

            ui.notify(
                "Notice: We are making updates to the OTTER web interface! The basic functionality should work as expected. But, please be patient with us if things are not working as expected!",
                position="bottom",
                close_button="OK!",
                type="warning",
                timeout=0
            )
            
        # Display the initial
        with ui.grid(rows="40px auto").classes("w-full") as grid:            
            ui.label(
                "Simple Search Form"
            ).classes("text-h4")
            partial_show_form()

        ui.label("Search Results").classes("text-h4")
        post_table([]) # start with an empty results table

        ui.button(
            "Download Results",
            on_click=lambda: search_results.write_results_to_zip()
        )

    
