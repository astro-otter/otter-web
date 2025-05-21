import os
import io
import zipfile
import json
import logging

from nicegui import ui, events
from ..theme import frame
from ..config import API_URL, WEB_BASE_URL
from .home import _post_table

from functools import partialmethod, partial
from dataclasses import dataclass

from astropy.coordinates import SkyCoord

from otter import Otter, util

db = Otter(url=API_URL)
logger = logging.getLogger(__name__)

class SearchInput:

    def __init__(self):
        self.search_kwargs = {}

    def update(self, e, key):
        self.search_kwargs[key] = e.value

    add_name = partialmethod(update, key='names')
    add_minz = partialmethod(update, key='minz')
    add_maxz = partialmethod(update, key='maxz')
    add_ra = partialmethod(update, key='ra')
    add_dec = partialmethod(update, key='dec')
    add_radius = partialmethod(update, key='radius')
    add_hasphot = partialmethod(update, key='hasphot')
    add_spec_classed = partialmethod(update, key='spec_classed')
    add_unambiguous = partialmethod(update, key='unambiguous')
    add_ra_unit = partialmethod(update, key='ra_unit')
    add_classification = partialmethod(update, key='classification')

@dataclass
class SearchResults:
    results: list[dict]

    @ui.refreshable
    def write_results_to_zip(self):
        """
        Writes the search results to a zipfile in memory to stage for download

        Modified from https://stackoverflow.com/questions/2463770/python-in-memory-zip-library
        """
        if self.results is None:
            ui.notify("You must do a search to download search results!")
            return

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for data in self.results:
                file_name = f"{data.default_name}.json"
                file_str = io.BytesIO(
                    bytes(
                        json.dumps(dict(data), indent=4),
                        encoding="utf-8"
                    )
                )
                zip_file.writestr(file_name, file_str.getvalue())


        ui.download(
            zip_buffer.getvalue(),
            "search-results.zip"
        )
        
def do_search(search_input, search_results, post_table):
    ui.notify('Search Initiated...')

    # do some validation
    if (
            'ra' in search_input.search_kwargs or
            'dec' in search_input.search_kwargs
    ):
        # then we need all four of those
        try:
            assert 'ra' in search_input.search_kwargs
            assert 'dec' in search_input.search_kwargs
            assert 'ra_unit' in search_input.search_kwargs

        except AssertionError:
            ui.notify(
                'If RA or Dec is provided then the RA, Dec, RA Unit, and Dec Unit must all be provided!'
            )
        
            
    # now do some cleaning
    if 'ra' in search_input.search_kwargs:
        search_input.search_kwargs['coords'] = SkyCoord(
            search_input.search_kwargs['ra'],
            search_input.search_kwargs['dec'],
            unit = (
                search_input.search_kwargs['ra_unit'],
                'deg' # assume always in degrees
            )
        )

    res = db.get_meta(**search_input.search_kwargs)
    search_results.results = res
    logger.info(res)
    post_table.refresh(res)
    ui.notify("Search Completed!")

def submit_form_with_enter(
        event:events.KeyEventArguments,
        search_input,
        search_results,
        post_table
) -> None:
    if event.key.enter and event.action.keydown:
        do_search(
            search_input,
            search_results,
            post_table
        )
    
def search_form(search_results, post_table):

    search_input = SearchInput()

    with ui.grid(columns=3):
        names = ui.input(
            'Transient Name',
            placeholder='Enter a transient name or partial name',
            on_change = search_input.add_name
        )

        ra = ui.input(
            'RA',
            placeholder='Enter an RA',
            on_change = search_input.add_ra
        )

        radius = ui.number(
            'Search Radius (")',
            placeholder='Default is 5"',
            on_change = search_input.add_radius
        )

        searchclass = ui.select(
            util._KNOWN_CLASS_ROOTS,
            label = 'Classification',
            on_change = search_input.add_classification
        )

        dec = ui.input(
            'Declination (deg.)',
            placeholder='Enter a Dec. (deg.)',
            on_change = search_input.add_dec
        )

        maxz = ui.number(
            'Maximum Redshift',
            placeholder='Enter a maximum redshift',
            on_change = search_input.add_maxz
        )
        
        unit_options = ['hourangle', 'degree']
        ra_unit = ui.select(
            unit_options,
            label = 'RA Unit',
            value = unit_options[0],
            on_change = search_input.add_ra_unit
        )
        search_input.add_ra_unit(ra_unit)
        
        minz = ui.number(
            'Minimum Redshift',
            placeholder='Enter a minimum redshift',
            on_change = search_input.add_minz
        )

        hasphot = ui.checkbox(
            "Has Photometry?",
            on_change = search_input.add_hasphot
        )

        hasspecclass = ui.checkbox(
            "Spectroscopically Confirmed?",
            on_change = search_input.add_spec_classed
        )

        unambiguous = ui.checkbox(
            "Unambiguously Classified?",
            on_change = search_input.add_unambiguous
        )

        
    ui.button('Submit').props('type="submit"').on_click(
        lambda: do_search(
            search_input,
            search_results,
            post_table
        )
    )

    ui.keyboard(
        on_key=lambda e: submit_form_with_enter(
            e,
            search_input,
            search_results,
            post_table
        ),
        ignore = ["select", "button", "textarea"]
    )

def raw_aql_query(post_table):
    query = """FOR transient IN transients
    RETURN transient
        """
        
    editor = ui.codemirror(
        value=f"{query}",
        language="AQL",
        on_change=lambda e : post_table.refresh(
            [r for r in db.AQLQuery(e.value, rawResults=True)]
        )
    ).classes("w-full")
    
# Function to switch between forms
def show_form(selected_form, search_results, post_table, containers=None):
    if containers is not None:
        for val in list(containers)[1:]:
            val.delete()
    if selected_form == 'Search Form':
        search_form(search_results, post_table)
    elif selected_form == 'AQL Query':
        raw_aql_query(post_table)
        
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
