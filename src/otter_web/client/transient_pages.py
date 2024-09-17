import json
from nicegui import ui
import numpy as np
import pandas as pd

from ..theme import frame
from ..config import API_URL

from otter import Otter
from otter.exceptions import FailedQueryError

from plotly import graph_objects as go
import matplotlib as mpl
from itertools import cycle

YAXES_IS_REVERSED = False
SNR_THRESHOLD = 1

def plot_lightcurve(phot, obs_label, fig, plot):

    fig.data = [] # clear the data from the figure
    
    cmap = mpl.colormaps['jet']
    n_lines = len(phot.filter_name.unique())
    colors = cmap(np.linspace(0, 1, n_lines))

    for (band, grp_all), c in zip(phot.groupby('filter_name'), colors):

        # make an approximate cut on "SNR" (really just flux/flux_err)

        if obs_label == 'UV/Optical/IR': 
            grp = grp_all[grp_all.converted_flux/grp_all.converted_flux_err > SNR_THRESHOLD]
        else:
            grp = grp_all

        grp["marker"] = grp.apply(
            lambda row : "triangle-down" if row.upperlimit else "circle",
            axis = 1
        )
            
        fig.add_scatter(
            x = grp.converted_date,
            y = grp.converted_flux,
            error_y = dict(array=grp.converted_flux_err),
            name = band,
            marker = dict(
                color=mpl.colors.to_hex(c),
                symbol=grp.marker,
                size=10
            ),
            mode = 'markers'
        )

    if obs_label == 'Radio':
        ylabel = 'Flux Density [mJy]'
    elif obs_label == 'UV/Optical/IR':
        ylabel = 'AB Magnitude'
    elif obs_label == 'X-Ray':
        ylabel = 'Flux Density [uJy]'
    else:
        raise ValueError('Invalid plot label!')
        
    fig.update_layout(
        dict(
            xaxis = dict(title='Date'),
            yaxis = dict(title=ylabel)
        )
    )

    if obs_label == 'UV/Optical/IR':
        fig.update_yaxes(autorange='reversed')
    if obs_label in {"Radio", "X-Ray"} and fig.layout.yaxis.autorange == 'reversed':
        fig.update_yaxes(autorange=True)
        
    plot.update()

def generate_property_table(meta):
    columns = [
        {
            "name": "prop",
            "label": "Property",
            "field": "prop",
            "required": True,
            "sortable": False,
            "align": "left"
        },
        {
            "name": "val",
            "label": "Value",
            "field": "val",
            "required": True,
            "sortable": False,
            "align": "left"
        }
    ]

    rows = [
        # list possible aliases
        {
            'prop': 'Aliases',
            'val': "; ".join(
                [f'{i["value"]}' for i in meta['name']['alias']]
            )
        },

        # give coordinates
        {
            'prop': 'Coordinate',
            'val': meta.get_skycoord().to_string("hmsdms") 
        }
    ]

    # get default classification
    default_class = meta.get_classification()
    if default_class is not None:
        rows.append(
            {
                'prop': "Default Classification (Our Confidence)",
                "val": f"{default_class[0]} (Confidence = {default_class[1]})"
            }   
        )

    # get the redshift
    z = meta.get_redshift()
    if z is not None:
        rows.append(
            {
                'prop': "Redshift",
                "val": z
            }
        )
        
    # get the discovery date
    try:
        default_disc_date = meta.get_discovery_date()
        rows.append(
            {
                "prop": "Discovery Date",
                "val": default_disc_date.iso
            }
        )
    except:
        pass
    
    table = (
        ui.table(columns=columns, rows=rows, row_key="prop", pagination=len(rows))
        .props("flat")
        .classes("w-full")
    )
    
    return table
    
@ui.page('/transient/{transient_default_name}')
def transient_subpage(transient_default_name:str):

    db = Otter(url=API_URL)
    meta = db.get_meta(names=transient_default_name)[0]
    dataset = db.query(names=transient_default_name)[0]
    json_data = json.dumps(dict(dataset), indent=4)
    
    phot_types = {}
    obs_types = {
        'radio':'mJy',
        'uvoir':'mag(AB)',
        'xray':'uJy'
    }
    label_map = {
        'radio' : 'Radio',
        'xray' : 'X-Ray',
        'uvoir' : 'UV/Optical/IR'
    }

    for obs_type, u in obs_types.items():
        try:
            phot = db.get_phot(
                names = transient_default_name,
                flux_unit = u,
                date_unit = 'iso',
                return_type = 'pandas',
                obs_type = obs_type
            )
            phot_types[label_map[obs_type]] = phot
            
        except FailedQueryError:
            pass

    hasphot = len(phot_types) > 0
    
    with frame():
        with ui.grid(columns=6).classes('w-full gap-0'):
            ui.label(f'{transient_default_name}').classes("col-span-5 text-h4")
            ui.button(
                "Download Dataset",
                on_click=lambda: ui.download(
                    bytes(json_data, encoding="utf-8"),
                    f"{transient_default_name}.json"
                ).classes("col-span-1")
            )
            
        ui.label(f'Properties').classes("text-h6")
        table = generate_property_table(meta)
        
        if hasphot:
            ui.label(f'Plots').classes("text-h6")

            fig = go.Figure()
            plot = ui.plotly(fig)


            plot_options = list(phot_types.keys())
            plot_toggle = ui.toggle(
                plot_options,
                value=plot_options[0],
                on_change=lambda e : plot_lightcurve(
                    phot_types[e.value],
                    e.value,
                    fig,
                    plot
                )
            )

            plot_lightcurve(phot_types[plot_options[0]], plot_options[0], fig, plot)            

            allphot = pd.concat(phot_types.values())
            try:
                phot_refs = ", ".join(
                    allphot.human_readable_refs.unique()
                )
                ui.label(f'Photometry Sources: {phot_refs}')
            except:
                print(allphot.human_readable_refs)
                ui.label(f'Photometry Sources: ERROR DISPLAYING!')
