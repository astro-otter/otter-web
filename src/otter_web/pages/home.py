import pandas as pd
from nicegui import ui
import httpx
from ..theme import frame
from ..utils import _parse_cat_table
import plotly.express as px

from otter_web.server.models import TransientRead
from astropy.coordinates import SkyCoord

API_URL = "http://127.0.0.1:10202"


@ui.page("/")
async def page():
    with frame():
        ui.label("All Transients").classes("text-h4")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/transients/", params={"limit": 999})
            all_events = response.json()

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
            {"name": "ra", "label": "RA", "field": "ra", "sortable": False},
            {"name": "dec", "label": "Dec", "field": "dec", "sortable": False},
            {"name": "date", "label": "Date", "field": "date", "sortable": False},
        ]

        table = (
            ui.table(columns=columns, rows=[], row_key="id", pagination=10)
            .props("flat")
            .classes("w-full")
        )

        for i, event_json in enumerate(all_events):
            event = TransientRead(**event_json)
            coord_string = SkyCoord(
                event.coordinates[0].ra, event.coordinates[0].dec
            ).to_string("hmsdms", sep=":", precision=2)

            table.add_rows(
                {
                    "id": f"{i}",
                    "name": event.name.default_name,
                    "ra": coord_string.split(" ")[0],
                    "dec": coord_string.split(" ")[1],
                    "date": (
                        event.date_references[0].value.strftime("%Y-%m-%d")
                        if len(event.date_references) > 0
                        else "No Date"
                    ),
                }
            )

        ui.label("Example Query").classes("text-h4")

        query = """SELECT transient.id, name.default_name, datereference.value AS date_reference
FROM transient
JOIN name ON name.transient_id = transient.id
JOIN datereference ON datereference.transient_id = transient.id
ORDER BY datereference.value DESC
LIMIT 10;
"""

        with httpx.Client() as client:
            response = client.get(
                f"{API_URL}/execute_query/",
                params={"sql": query},
                follow_redirects=True,
            )
            response_json = response.json()

        editor = ui.codemirror(f"{query}", language="SQL").classes("w-full")

        with ui.card().props("flat bordered").classes("w-full"):
            text_area = ui.html(f"{response.json()}").classes("w-full")
