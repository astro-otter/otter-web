import os
import json
from nicegui import ui, context
import numpy as np
import pandas as pd
import time

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
ADS_BASE_URL = "https://ui.adsabs.harvard.edu/abs/"
ALLOWED_NON_BIBS = {
    "TNS",
    "ASAS-SN",
    "ATLAS",
    "Pan-STARRS",
    "GaiaAlerts",
    "ZTF",
    "WISeREP",
    "SOUSA"
}

DELTA_T = 10
MIN_T = 0
MAX_T = None
XAXIS = "Frequency [GHz]"

import logging
logger = logging.getLogger("otter-log")

def plot_lightcurve(phot, obs_label, fig, plot, meta, show_limits=True):

    if len(phot) == 0:
        for trace in fig.data:
            trace.visible = 'legendonly'
        plot.update()
        return

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

        # filter out upperlimits if show_limits is false
        if not show_limits:
            grp = grp[~grp.upperlimit]

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
            y = grp.converted_flux.astype(float),
            error_y = dict(array=grp.converted_flux_err.astype(float)),
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
        yaxis_type = "log"
    elif obs_label == 'UV/Optical/IR':
        ylabel = 'AB Magnitude'
        yaxis_type = "linear"
    elif obs_label == 'X-Ray':
        ylabel = 'Flux Density [uJy]'
        yaxis_type = "log"
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
            Time(disc_date - 2*365, format="mjd").iso,
            Time(
                min(Time(
                    phot.converted_date.astype(str).tolist(),
                    format="iso"
                )).mjd - 50,
                format="mjd"
            ).iso
        ),
        min(
            Time(disc_date + 365*8, format="mjd").iso,
            Time(
                max(Time(
                    phot.converted_date.astype(str).tolist(),
                    format="iso"
                )).mjd + 50,
                format="mjd"
            ).iso
        )
    ) # -2 < t/years < 8

    fluxes = phot[~phot.upperlimit].converted_flux
    outlier_limit = 5*np.std(fluxes)
    flux_mean = np.mean(fluxes)
    if yaxis_type == "log":
        phot_range = (
            max(0, flux_mean - outlier_limit),
            np.log10(flux_mean + outlier_limit)
        )
    else:
        phot_range = (
            max(-1, flux_mean - outlier_limit),
            flux_mean + outlier_limit
        )

    # update the axis with labels and ranges
    fig.update_layout(
        dict(
            xaxis = dict(
                title='Date',
            ),
            yaxis = dict(
                title=ylabel,
                type=yaxis_type
            ),
        )
    )
        
    if obs_label == 'UV/Optical/IR':
        fig.update_yaxes(autorange='reversed')
    if obs_label in {"Radio", "X-Ray"} and fig.layout.yaxis.autorange == 'reversed':
        fig.update_yaxes(autorange=True)
        
    plot.update()

def plot_sed(phot, fig, plot, meta):

    global DELTA_T
    dt = DELTA_T

    global MIN_T
    start_time = MIN_T

    global MAX_T
    end_time = MAX_T

    global XAXIS
    xaxis = XAXIS
    
    fig.data = [] # clear the data from the figure
    
    disc_date = meta.get_discovery_date()
    if disc_date is None:
        disc_date = phot.converted_date.min()
    else:
       disc_date = disc_date.mjd     
    phot["dt"] = phot.converted_date.astype(float) - disc_date

    if end_time is None:
        end_time = phot.dt.max()
    
    max_t = min(phot.dt.max(), end_time)
    min_t = max(phot.dt.min(), start_time)
    
    cmap = mpl.colormaps['jet']
    n_lines = int((max_t - min_t) // dt)
    colors = cmap(np.linspace(0, 1, n_lines))
    
    color_idx = 0 
    curr_time = start_time

    if xaxis == "Frequency [GHz]":
        xaxis_key = "converted_freq"
    elif xaxis == "Wavelength [nm]":
        xaxis_key = "converted_wave"

    while curr_time+dt < max_t:
        c = colors[color_idx]

        grp = phot[(phot.dt >= curr_time) * (phot.dt < curr_time+dt)]
        if len(grp) == 0:
            curr_time += dt
            continue

        grp["marker"] = grp.apply(
            lambda row : "triangle-down" if row.upperlimit else "circle",
            axis = 1
        )

        grp["converted_flux_err"] = grp.apply(
            lambda row : None if row.upperlimit else row.converted_flux_err,
            axis = 1
        )
        
        fig.add_scatter(
            x = grp[xaxis_key].astype(float),
            y = grp.converted_flux.astype(float),
            error_y = dict(array=grp.converted_flux_err.astype(float)),
            name = f"{curr_time}-{curr_time+dt}",
            marker = dict(
                color=mpl.colors.to_hex(c),
                symbol=grp.marker,
                size=10
            ),
            mode = 'markers'
        )

        curr_time += dt
        color_idx += 1

    exp_form = "power"
    fig.update_layout(
        dict(
            xaxis = dict(
                title=XAXIS,
                type = "log",
                exponentformat  = exp_form
            ),
            yaxis = dict(
                title="Flux Density [Jy]",
                type="log",
                exponentformat = exp_form
            ),
            legend_title_text = "Time Since Discovery",
        )
    )

    plot.update()
        
def generate_property_table(meta):

    # get all of the references for the metadata table
    name_refs = []
    for r in meta["name"]["alias"]:
        n = r["reference"]
        if not isinstance(n, list):
            n = [n]
        for val in n:
            if val in ALLOWED_NON_BIBS:
                name_refs.append(val)
            else:
                name_refs.append(f"<u><a href={ADS_BASE_URL+val}>{val}</a></u>")
    name_ref_strs_uq = np.unique(name_refs)

    coord_refs = []
    for r in meta["coordinate"]:
        n = r["reference"]
        if not isinstance(n, list):
            n = [n]
        for val in n:
            if val in ALLOWED_NON_BIBS:
                coord_refs.append(val)
            else:
                coord_refs.append(f"<u><a href={ADS_BASE_URL+val}>{val}</a></u>")
    coord_ref_strs_uq = np.unique(coord_refs)

    class_ref_strs_uq = ""
    if "classification" in meta:
        class_refs = []
        for r in meta["classification"]["value"]:
            n = r["reference"]
            if not isinstance(n, list):
                n = [n]
            for val in n:
                if val in ALLOWED_NON_BIBS:
                    class_refs.append(val)
                else:
                    class_refs.append(f"<u><a href={ADS_BASE_URL+val}>{val}</a></u>")
        class_ref_strs_uq = np.unique(class_refs)
                    
    redshift_ref_strs_uq = ""
    if "distance" in meta:
        redshift_refs = []
        for r in meta["distance"]:
            if r["distance_type"] != "redshift": continue
            n = r["reference"]
            if not isinstance(n, list):
                n = [n]
            for val in n:
                if val in ALLOWED_NON_BIBS:
                    redshift_refs.append(val)
                else:
                    redshift_refs.append(f"<u><a href={ADS_BASE_URL+val}>{val}</a></u>")
        redshift_ref_strs_uq = np.unique(redshift_refs)

    disc_date_ref_strs_uq = ""
    if "date_reference" in meta:
        disc_date_refs = []
        for r in meta["date_reference"]:
            if r["date_type"] != "discovery": continue
            n = r["reference"]
            if not isinstance(n, list):
                n = [n]
            for val in n:
                if val in ALLOWED_NON_BIBS:
                    disc_date_refs.append(val)
                else:
                    disc_date_refs.append(f"<u><a href={ADS_BASE_URL+val}>{val}</a></u>")
        disc_date_ref_strs_uq = np.unique(disc_date_refs)

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
        },
        {
            "name": "ref",
            "label": "References",
            "field": "ref",
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
            ),
            'ref': "; ".join(
                [r for r in name_ref_strs_uq]
            )
        },

        # give coordinates
        {
            'prop': 'Coordinate',
            'val': meta.get_skycoord().to_string("hmsdms"),
            'ref': "; ".join(
                [r for r in coord_ref_strs_uq]
            )
        }
    ]

    # get default classification
    try:
        classes = ", ".join(
            f'{c["object_class"]} (C={c["confidence"]})' for c in meta["classification"]["value"]
        )
        rows.append(
            {
                'prop': "Classifications (Flag)",
                "val": f"{classes}",
                "ref": "; ".join(
                    [r for r in class_ref_strs_uq]
                )
            }   
        )

    except Exception:
        pass

    # get the redshift
    try:
        z = meta.get_redshift()
        rows.append(
            {
                'prop': "Redshift",
                "val": z,
                "ref": "; ".join(
                    [r for r in redshift_ref_strs_uq]
                )
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
                    "val": default_disc_date.iso,
                    "ref": "; ".join(
                        [r for r in disc_date_ref_strs_uq]
                    )

                }
            )
            
    except KeyError:
        pass
    
    table = (
        ui.table(columns=columns, rows=rows, row_key="prop", pagination=len(rows))
        .props("flat")
        .classes("w-full")
        .add_slot("body-cell-ref", '<q-td v-html="props.row.ref"></q-td>')
    )
    
    return table

def _update_global_delta_t(new_delta_t, *args, **kwargs):
    global DELTA_T
    DELTA_T = new_delta_t
    plot_sed(*args, **kwargs)

def _update_global_min_t(new_min_t, *args, **kwargs):
    global MIN_T
    MIN_T = new_min_t
    plot_sed(*args, **kwargs)

def _update_global_max_t(new_max_t, *args, **kwargs):
    global MAX_T
    MAX_T = new_max_t
    plot_sed(*args, **kwargs)

def _update_global_xaxis(new_xaxis, *args, **kwargs):
    global XAXIS
    XAXIS = new_xaxis
    plot_sed(*args, **kwargs)

async def _load_phot(db, transient_default_name, obs_types, label_map):
    phot_types = {}
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

    try:
        allphot = db.get_phot(
            names = transient_default_name,
            flux_unit = "Jy",
            date_unit = "mjd",
            return_type = "pandas"
        )
    except FailedQueryError:
        allphot = None
        
    return allphot, phot_types

@ui.page(os.path.join(WEB_BASE_URL, 'transient', '{transient_default_name}'))
async def transient_subpage(transient_default_name:str):

    global DELTA_T
    global MIN_T
    global MAX_T

    logger.info("Connecting to the database and loading metadata...")
    db = Otter(url=API_URL)
    meta = db.get_meta(names=transient_default_name)[0]
    dataset = db.query(names=transient_default_name)[0]
    json_data = json.dumps(dict(dataset), indent=4)
    
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

    start = time.time()
    logger.info("Loading photometry...")
    allphot, phot_types = await _load_phot(
        db,
        transient_default_name,
        obs_types,
        label_map
    )
    logger.info(f"Loading the photometry took {time.time()-start}s")
    
    hasphot = len(phot_types) > 0

    fov_arcmin = 1.5
    fov_deg = fov_arcmin / 60

    logger.info("Adding aladin viewer and photometry plots...")
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
        
        ui.label(f'Properties').classes("text-h6")
        table = generate_property_table(meta)
        
        if hasphot:
            # ui.label(f'Plots').classes("text-h3")

            with ui.row().classes('w-full gap-10'):
                
                # Light curves
                with ui.column():
                    ui.label(f'Light Curves').classes("text-h6")
                    
                    fig_lc = go.Figure()
                    plot_lc = ui.plotly(fig_lc)

                    plot_options = list(phot_types.keys())

                    with ui.row():
                        plot_toggle = ui.toggle(
                            plot_options,
                            value=plot_options[0],
                            on_change=lambda e : plot_lightcurve(
                                phot_types[e.value],
                                e.value,
                                fig_lc,
                                plot_lc,
                                meta
                            )
                        )

                        show_limits = ui.checkbox(
                            "Show Upperlimits?",
                            value = True,
                            on_change = lambda e : plot_lightcurve(
                                phot_types[plot_toggle.value],
                                plot_toggle.value,
                                fig_lc,
                                plot_lc,
                                meta,
                                show_limits=bool(e.value)
                            )
                        )

                        ui.button(
                            "Clear All",
                            on_click = lambda : plot_lightcurve(
                                [], # pass an empty phot dataframe
                                plot_toggle.value,
                                fig_lc,
                                plot_lc,
                                meta,
                                show_limits=bool(show_limits.value)
                            )
                        )

                        ui.button(
                            "Plot All",
                            on_click = lambda : plot_lightcurve(
                                phot_types[plot_toggle.value],
                                plot_toggle.value,
                                fig_lc,
                                plot_lc,
                                meta,
                                show_limits=bool(show_limits.value)
                            )
                        )

                        
                    plot_lightcurve(
                        phot_types[plot_options[0]],
                        plot_options[0],
                        fig_lc,
                        plot_lc,
                        meta,
                        show_limits=bool(show_limits.value)
                    )                            

                # SED
                with ui.column():
                    ui.label("Spectral Energy Distribution").classes("text-h6")

                    sed_fig = go.Figure()
                    sed_plot = ui.plotly(sed_fig)
                    
                    with ui.row():
                        dt_input = ui.number(
                            label="dt = ",
                            value=DELTA_T,
                            on_change=lambda e : _update_global_delta_t(
                                e.value,
                                allphot,
                                sed_fig,
                                sed_plot,
                                meta
                            )
                        )
                        with dt_input.add_slot("prepend"):
                            with ui.icon("help"):
                                ui.tooltip("The delta time to split the data by. This is the time range used when grouping the SED data.")
                        
                        mintime_input =  ui.number(
                            label="Min. Time = ",
                            value=MIN_T,
                            on_change=lambda e:_update_global_min_t(
                                e.value,
                                allphot,
                                sed_fig,
                                sed_plot,
                                meta
                            )
                        )
                        with mintime_input.add_slot("prepend"):
                            with ui.icon("help"):
                                ui.tooltip("The minimum time to consider when grouping the dataset.")

                        maxtime_input = ui.number(
                            label="Max. Time = ",
                            value=MAX_T,
                            on_change=lambda e:_update_global_max_t(
                                e.value,
                                allphot,
                                sed_fig,
                                sed_plot,
                                meta
                            )
                        )
                        with maxtime_input.add_slot("prepend"):
                            with ui.icon("help"):
                                ui.tooltip("The maximum time to consider when grouping the dataset.")

                        ui.select(
                            ["Frequency [GHz]", "Wavelength [nm]"],
                            value = "Frequency [GHz]",
                            label='x-axis',
                            on_change=lambda e : _update_global_xaxis(
                                e.value,
                                allphot,
                                sed_fig,
                                sed_plot,
                                meta
                            )
                        )
                        
                    plot_sed(
                        allphot,
                        sed_fig,
                        sed_plot,
                        meta
                    )
                    
            all_phot_refs = []
            all_phot_hrns = []
            for ref, hrn in zip(allphot.reference, allphot.human_readable_refs):
                if isinstance(ref, list):
                    all_phot_refs += ref
                else:
                    all_phot_refs.append(ref)
                if isinstance(hrn, list):
                    all_phot_hrns += hrn
                else:
                    all_phot_hrns.append(hrn)

            ui.label(f'Photometry Sources:')

            uq_bibs, idx = np.unique(all_phot_refs, return_index=True)
            with ui.list().props('dense'):
                for bibcode in uq_bibs:
                    with ui.item():
                        ui.link(bibcode, f"{ADS_BASE_URL}{bibcode}")

        logger.info("Successfully load the page!")
