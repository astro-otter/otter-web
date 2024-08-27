import pandas as pd
from nicegui import ui
import plotly.express as px

from ..theme import frame
from ..config import API_URL
from ..models import TransientRead

from otter import Otter

from astropy.coordinates import SkyCoord
from astropy.time import Time

db = Otter(url=API_URL)

@ui.page("/")
async def page():
    with frame():
        ui.label("All Transients").classes("text-h4")

        all_events = db.query(raw=True)

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
            print(event_json['name'])
            event = TransientRead(**event_json)
            
            coord_string = SkyCoord(
                event.coordinate[0].ra, event.coordinate[0].dec, unit=(
                    event.coordinate[0].ra_units,
                    event.coordinate[0].dec_units
                )
            ).to_string("hmsdms", sep=":", precision=2)

            table.add_rows(
                {
                    "id": f"{i}",
                    "name": event.name.default_name,
                    "ra": coord_string.split(" ")[0],
                    "dec": coord_string.split(" ")[1],
                    "date": (
                        Time(
                            str(event.date_reference[0].value).strip(),
                            format=event.date_reference[0].date_format
                        ).strftime("%Y-%m-%d")
                        if len(event.date_reference) > 0
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

        editor = ui.codemirror(f"{query}", language="AQL").classes("w-full")
