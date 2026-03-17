import os
import logging
from functools import partial

from nicegui import ui, events
from ..theme import frame
from ..config import API_URL, WEB_BASE_URL
from ..models import TransientRead

from .search_util import _post_table, SearchResults, show_form

logger = logging.getLogger(__name__)

@ui.page(os.path.join(WEB_BASE_URL, "search"))
async def search():

    @ui.refreshable
    def post_table(*args, **kwargs):
        _post_table(*args, **kwargs)
    
    search_results = SearchResults(None)

    partial_show_form = partial(
        show_form,
        search_results=search_results,
        post_table=post_table
    )
    
    with frame():

        ui.label("Search OTTER").classes("col-span-5 text-h4")
            
        # Display the initial
        with ui.grid(rows="40px auto").classes("w-full") as grid:
            selected_tab = ui.toggle(
                ['Search Form', 'AQL Query'],
                value='Search Form',
                on_change=lambda e: partial_show_form(e.value, containers=grid)
            ).style("width:20.8%")
            
            partial_show_form(selected_tab.value)

        ui.label("Search Results").classes("text-h4")
        post_table([]) # start with an empty results table

        ui.button(
            "Download Results",
            on_click=lambda: search_results.write_results_to_zip()
        )
