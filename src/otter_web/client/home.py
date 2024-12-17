import pandas as pd
from nicegui import ui
from typing import List

from plotly import graph_objects as go
from plotly.subplots import make_subplots

from ..theme import frame
from ..config import API_URL
from ..models import TransientRead

from .transient_pages import *

from otter import Otter, Transient

from astropy.coordinates import SkyCoord
from astropy import coordinates as coord
from astropy.time import Time
from astropy import units as u

import logging
logger = logging.getLogger(__name__)


logger.info(API_URL)
logger.info(f"Opening API server on {API_URL}...")
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

def skymap(fig, tdes):
    '''
    Generates a skymap of the locations of the tdes
    '''

    fig.update_geos(
        projection_type="mollweide",
        showland=False,
        showcoastlines=False,
        showframe=True,
        lonaxis=dict(showgrid=True, dtick=30),
        lataxis=dict(showgrid=True, dtick=30),
        bgcolor="#eff3f8"#'rgba(0,0,0,0)'
    )

    info = {'RA [deg]':[],
            'Dec [deg]':[],
            'TDE Name':[],
            'Z': []
            }

    for t in tdes:

        t = Transient(t)

        skycoord = t.get_skycoord()
        
        info['RA [deg]'].append(skycoord.ra)
        info['Dec [deg]'].append(skycoord.dec)
        info['TDE Name'].append(t.default_name)

        try:
            z = t.get_redshift()
            if z is not None:
                info['Z'].append(z)
            else:
                info['Z'].append(0)

        except KeyError:
            info['Z'].append(0)
                
    info['RA [deg]'] = coord.Angle(info['RA [deg]'], unit=u.hourangle)
    info['Dec [deg]'] = coord.Angle(info['Dec [deg]'], unit=u.deg)
    
    info['RA [deg]'] = info['RA [deg]'].deg
    info['Dec [deg]'] = info['Dec [deg]'].deg

    info = pd.DataFrame(info)
    
    info['Z'] = info['Z'].astype(float)
    
    for lon in np.arange(0, 360, 30):
        fig.add_trace(go.Scattergeo(lon=[lon, lon, lon],
                                    lat=[90, 0, -90],
                                    mode='lines+text',
                                    showlegend=False,
                                    text=["", f"{lon}", ""],
                                    textposition='bottom center',
                                    line=go.scattergeo.Line(width=1, dash='dot', color='grey')))
    for lat in [-90, -60, -30, 30, 60, 90]:
        fig.add_trace(go.Scattergeo(lon=[0, 180, 360], lat=[lat, lat, lat],
                                    mode='lines+text',
                                    text=[f"{lat}"],
                                    textposition="middle right",
                                    showlegend=False,
                                    line=go.scattergeo.Line(width=1, dash='dot', color='grey')))
        
    fig.add_trace(go.Scattergeo(lon=info['RA [deg]'],
                                lat=info['Dec [deg]'],
                                hovertext=info['TDE Name'],
                                hovertemplate="<b>Name</b>: %{hovertext}<br>" +
                                              "<b>RA</b>: %{lon}<br>" +
                                              "<b>Dec</b>: %{lat}<br>" +
                                              "<extra></extra>",
                                text=[f"""<a href="./transient/{name}" style="color:transparent">{name}</a>""" for name in info['TDE Name']],
                                textposition='middle center',
                                #textfont={"color":"transparent"},
                                showlegend=False,
                                marker=dict(color=np.log10(info['Z']),
                                            colorbar=dict(thickness=20,
                                                          title='log(z)'),
                                            colorscale="Thermal",
                                            size=10
                                            ),
                                mode='markers+text'
                                ),
                  )

    return fig

@ui.page("/")
async def page():
    with frame():
        imsize=32
        with ui.grid(rows=1, columns=16).classes("gap-0 no-wrap"):

            ui.image(
                "src/otter_web/static/logo.png"
            ).classes(f"w-{imsize} col-span-4")
            
            ui.label(
                "The Open mulTiwavelength Transient Event Repository"
            ).classes("text-h2 col-span-12")

            
        all_events = db.query(raw=True)

        fig = go.Figure(
            layout = dict(
                paper_bgcolor="#eff3f8", # 'rgba(0,0,0,0)',
                plot_bgcolor="#eff3f8", #'rgba(0,0,0,0)',
                height=600
            )
        )
        fig = skymap(fig, all_events)
        ui.plotly(fig).classes("w-full")
        
        ui.label("All Transients").classes("text-h4")
        post_table(all_events)

        '''
        # I'm commenting out the query box on the home page since it has moved
        # to the search page
        
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
        '''
