import os
import json
from nicegui import ui, context
import numpy as np
import pandas as pd

from astropy.time import Time

from ..theme import frame
from ..config import API_URL, WEB_BASE_URL

from otter import Otter
from otter.exceptions import FailedQueryError

from plotly import graph_objects as go
import matplotlib as mpl
from itertools import cycle

YAXES_IS_REVERSED = False
SNR_THRESHOLD = 1

def plot_lightcurve(phot, obs_label, fig, plot, meta):

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

        grp["converted_flux_err"] = grp.apply(
            lambda row : None if row.upperlimit else row.converted_flux_err,
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

    # set some date and flux limits to make the plots look a little prettier
    disc_date = meta.get_discovery_date()
    
    if disc_date is None:
        if np.all(phot.upperlimit):
            disc_date = Time(
                phot.converted_date.min(),
                format="iso"
            ).mjd - 10
        else:
            # then just use the first detection
            disc_date = Time(
                phot[~phot.upperlimit].converted_date.min(),
                format="iso"
            ).mjd - 10
    else:
        disc_date = disc_date.mjd

    date_range = (
        max(
            Time(disc_date - 365, format="mjd").iso,
            Time(
                Time(
                    phot.converted_date.min(),
                    format="iso"
                ).mjd - 10,
                format="mjd"
            ).iso
        ),
        min(
            Time(disc_date + 365*8, format="mjd").iso,
            Time(
                Time(
                    phot.converted_date.max(),
                    format="iso"
                ).mjd + 10,
                format="mjd"
            ).iso
        )
    ) # -2 < t/years < 8

    fluxes = phot[~phot.upperlimit].converted_flux
    outlier_limit = 5*np.std(fluxes)
    flux_mean = np.mean(fluxes)
    phot_range = (
        max(-1, flux_mean - outlier_limit),
        flux_mean + outlier_limit
    )

    # update the axis with labels and ranges
    fig.update_layout(
        dict(
            xaxis = dict(
                title='Date',
                range=date_range
            ),
            yaxis = dict(
                title=ylabel,
                range=phot_range
            )
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
    try:
        default_class = meta.get_classification()
        rows.append(
            {
                'prop': "Default Classification (Our Confidence)",
                "val": f"{default_class[0]} (Confidence = {default_class[1]})"
            }   
        )

    except KeyError:
        pass

    # get the redshift
    try:
        z = meta.get_redshift()
        rows.append(
            {
                'prop': "Redshift",
                "val": z
            }
        )
    except KeyError:
        pass
    
    # get the discovery date
    try:
        default_disc_date = meta.get_discovery_date()
        if default_disc_date is not None:
            rows.append(
                {
                    "prop": "Discovery Date",
                    "val": default_disc_date.iso
                }
            )
            
    except KeyError:
        pass
    
    table = (
        ui.table(columns=columns, rows=rows, row_key="prop", pagination=len(rows))
        .props("flat")
        .classes("w-full")
    )
    
    return table
    
@ui.page(os.path.join(WEB_BASE_URL, '/transient/{transient_default_name}'))
async def transient_subpage(transient_default_name:str):

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

    fov_arcmin = 1.5
    fov_deg = fov_arcmin / 60

    with frame():

        with ui.grid(columns=6):
            with ui.column().classes("align-left col-span-2"):
                with ui.row():
                    ui.label(f'{transient_default_name}').classes("text-h4")
                with ui.row():
                    ui.button(
                        "Download Dataset",
                        on_click=lambda: ui.download(
                            bytes(json_data, encoding="utf-8"),
                            f"{transient_default_name}.json"
                        )
                    )

            with ui.column().classes("col-span-3"):
                ui.element("div")
                    
            with ui.column().classes("align-right col-span-1"):
                aladin_parent = ui.element("div")
            
        # add aladin viewer
        aladin_viewer = f"""
        <div id="aladin-lite-div" style="width:200px;height:200px;"></div>
        <script type="text/javascript" src="https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js" charset="utf-8"></script>
        <script>
        let aladin;
        A.init.then( () => {{
            aladin = A.aladin('#aladin-lite-div', {{survey: 'https://alasky.cds.unistra.fr/DSS/DSSColor/', fov:{fov_deg}, target: "{meta.get_skycoord().to_string('hmsdms', sep=':')}"}});
        }});
        </script>
        """
        ui.add_body_html(aladin_viewer)
        element = ui.run_javascript(f"""
        var el = document.getElementById('aladin-lite-div');
        var parent = document.getElementById('c{aladin_parent.id}');
        parent.appendChild(el);
        """)
        print(element)
        
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
                    plot,
                    meta
                )
            )

            plot_lightcurve(
                phot_types[plot_options[0]],
                plot_options[0],
                fig,
                plot,
                meta
            )            

            allphot = pd.concat(phot_types.values())
            try:
                phot_refs = ", ".join(
                    allphot.human_readable_refs.unique()
                )
                ui.label(f'Photometry Sources: {phot_refs}')
            except:
                print(allphot.human_readable_refs)
                ui.label(f'Photometry Sources: ERROR DISPLAYING!')
