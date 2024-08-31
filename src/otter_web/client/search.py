from nicegui import ui
from ..theme import frame
from ..config import API_URL
from .home import post_table

from functools import partialmethod

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
    
    
def do_search(search_input):
    print(search_input.search_kwargs)
    ui.notify('Search Initiated...')
    res = db.get_meta(**search_input.search_kwargs)
    print(res)
    post_table.refresh(res)
    ui.notify("Search Completed!")
    
def search_form():

    search_input = SearchInput()
    
    names = ui.input(
        'Transient Name',
        placeholder='Enter a transient name or partial name',
        on_change = search_input.add_name
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
    
    print(search_input.search_kwargs)
    
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
        with ui.grid(rows=2) as grid:
            selected_tab = ui.toggle(
                ['Search Form', 'AQL Query'],
                value='Search Form',
                on_change=lambda e: show_form(e.value, grid)
            )
            
            show_form(selected_tab.value)

        ui.label("Search Results").classes("text-h4")
        post_table([]) # start with an empty results table
