from nicegui import ui
from ..theme import frame
from ..config import API_URL
from .home import post_table

from functools import partialmethod

from astropy.coordinates import SkyCoord

from otter import Otter

db = Otter(url=API_URL)

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
    add_ra_unit = partialmethod(update, key='ra_unit')
    add_dec_unit = partialmethod(update, key='dec_unit')
    
def do_search(search_input):
    ui.notify('Search Initiated...')

    # do some validation
    if (
            'ra' in search_input.search_kwargs or
            'dec' in search_input.search_kwargs or
            'ra_unit' in search_input.search_kwargs or
            'dec_unit' in search_input.search_kwargs
    ):
        # then we need all four of those
        try:
            assert 'ra' in search_input.search_kwargs
            assert 'dec' in search_input.search_kwargs
            assert 'ra_unit' in search_input.search_kwargs
            assert 'dec_unit' in search_input.search_kwargs
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
                search_input.search_kwargs['dec_unit']
            )
        )

        del search_input.search_kwargs['ra']
        del search_input.search_kwargs['dec']
        del search_input.search_kwargs['ra_unit']
        del search_input.search_kwargs['dec_unit']
    
    res = db.get_meta(**search_input.search_kwargs)
    print(res)
    post_table.refresh(res)
    ui.notify("Search Completed!")
    
def search_form():

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

        dec = ui.input(
            'Declination',
            placeholder='Enter a Dec.',
            on_change = search_input.add_dec
        )

        radius = ui.number(
            'Search Radius (")',
            placeholder='Default is 5"',
            on_change = search_input.add_radius
        )

        unit_options = ['hourangle', 'degree']
        ra_unit = ui.select(
            unit_options,
            label = 'RA Unit',
            on_change = search_input.add_ra_unit
        )
        dec_unit = ui.select(
            unit_options,
            label = 'Declination Unit',
            on_change = search_input.add_dec_unit
        )
        
        minz = ui.number(
            'Minimum Redshift',
            placeholder='Enter a minimum redshift',
            on_change = search_input.add_minz
        )
        maxz = ui.number(
            'Maximum Redshift',
            placeholder='Enter a maximum redshift',
            on_change = search_input.add_maxz
        )

        hasphot = ui.checkbox(
            "Has Photometry?",
            on_change = search_input.add_hasphot
        )
        
    ui.button('Submit').props('type="submit"').on_click(lambda: do_search(search_input))        

def raw_aql_query():
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
def show_form(selected_form, containers=None):
    if containers is not None:
        for val in list(containers)[1:]:
            val.delete()
    if selected_form == 'Search Form':
        search_form()
    elif selected_form == 'AQL Query':
        raw_aql_query()
        
@ui.page("/search")
async def search():
    with frame():

        ui.label("Search OTTER").classes("text-h4")
        
        # Display the initial
        with ui.grid(rows="40px auto").classes("w-full") as grid:
            selected_tab = ui.toggle(
                ['Search Form', 'AQL Query'],
                value='Search Form',
                on_change=lambda e: show_form(e.value, grid)
            ).style("width:20.8%")
            
            show_form(selected_tab.value)

        ui.label("Search Results").classes("text-h4")
        post_table([]) # start with an empty results table
