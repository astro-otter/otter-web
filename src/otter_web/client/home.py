import pandas as pd
from nicegui import ui
import plotly.express as px
from typing import List


from ..theme import frame
from ..config import API_URL
from ..models import TransientRead

from .transient_pages import *

from otter import Otter, Transient

from astropy.coordinates import SkyCoord
from astropy.time import Time

db = Otter(url=API_URL)

@ui.refreshable
def post_table(events:List[dict]) -> None:
    columns = [
        {
            "name": "id",
            "label": "ID",
            "field": "id",
            "required": True,
            "sortable": True,
            "align": "left",
            "classes": "hidden",
            "headerClasses": "hidden",
        },
        {
            "name": "name",
            "label": "Name",
            "field": "name",
            "required": True,
            "sortable": True,
            "align": "left",
        },
        {
            "name": "class",
            "label": "Classification",
            "field": "class",
            "required": True,
            "sortable": True,
            "align": "left"
        },
        {"name": "ra", "label": "RA", "field": "ra", "sortable": False},
        {"name": "dec", "label": "Dec", "field": "dec", "sortable": False},
        {"name": "date", "label": "Discovery Date", "field": "date", "sortable": False},
    ]

    table = (
        ui.table(columns=columns, rows=[], row_key="id", pagination=10)
        .props("flat")
        .classes("w-full")
    )
    
    for i, event_json in enumerate(events):
        event = TransientRead(**event_json)
        try:
            disc_date = Transient(event_json).get_discovery_date()
        except (KeyError, TypeError):
            disc_date = None
            
        coord_string = SkyCoord(
            event.coordinate[0].ra, event.coordinate[0].dec, unit=(
                event.coordinate[0].ra_units,
                event.coordinate[0].dec_units
            )
        ).to_string("hmsdms", sep=":", precision=2)

        try:
            default_class = Transient(event_json).get_classification()[0]
        except (KeyError, TypeError):
            default_class = None
        
        table.add_rows(
            {
                "id": f"{i}",
                "name": event.name.default_name,
                "class": default_class if default_class is not None else "Unknown Class",
                "ra": coord_string.split(" ")[0],
                "dec": coord_string.split(" ")[1],
                "date": (
                    disc_date.strftime("%Y-%m-%d")
                    if disc_date is not None
                    else "No Date"
                ),
            }
        )

    table.add_slot(
        'body-cell-title',
        r'<td><a :href="props.row.url">{{ props.row.title }}</a></td>'
    )
    table.on('rowClick', lambda e : ui.navigate.to(f'/transient/{e.args[1]["name"]}'))
        
@ui.page("/")
async def page():
    with frame():
        ui.label("All Transients").classes("text-h4")

        all_events = db.query(raw=True)
        post_table(all_events)

        ui.label("Editable AQL Query for the above Table").classes("text-h4")

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
