import os

from nicegui import ui, app, context, background_tasks
from plotly import graph_objects as go
import numpy as np

import redback
from bilby.core.prior.analytical import Uniform, LogUniform

from typing import Callable, Dict, Any
from ..config import API_URL, WEB_BASE_URL
from ..theme import frame

NSTEPS = 100

LIGHTCURVE_MODELS = [
    "afterglow_models",
    "fireball_models",
    #"gaussianprocess_models",
    "integrated_flux_afterglow_models",
    "kilonova_models",
    "magnetar_models",
    "magnetar_driven_ejecta_models",
    "phase_models",
    "phenomenological_models",
    "prompt_models",
    "shock_powered_models",
    "supernova_models",
    "tde_models",
]

SPECTRAL_MODELS = [
    "general_synchrotron_models",
    "spectral_models",
    "stellar_interaction_models"
]

@ui.page(os.path.join(WEB_BASE_URL, "redback_interactive"))
async def redback_plot():
    
    model_dict = redback.model_library.all_models_dict

    all_model_names = []
    for module_name in LIGHTCURVE_MODELS:
        all_model_names += redback.model_library.modules_dict[module_name]
        
    all_model_names = [m for m in all_model_names if not m.startswith("_")]

    with frame():

        ui.label("OTTER x Redback").classes("text-h2")
        ui.restructured_text("Use this tool to plot >600 models implemented in Redback on top of OTTER data.")
        
        ui.input(
            label="Search the model library...",
            on_change=lambda e : display_object_list.refresh(
                [name for name in all_model_names if e.value in name]
            )
        )

        display_object_list(all_model_names)
        
        add_dynamic_plotly_controls("arnett")

def _get_model_parameters(model_name):

    if model_name is None: return None, None
    
    priors = redback.priors.get_priors(model_name)
    model_dict = redback.model_library.all_models_dict

    parameters = {}
    for name, p in priors.items():
        parameters[name] = {}

        if isinstance(p, LogUniform):
            # use log scaling for the slider
            min_, max_ = np.log10(p.minimum), np.log10(p.maximum)
            scale = "log"
            label = f"log10({name})"
        else:
            # use linear scaling for the slider
            min_, max_ = p.minimum, p.maximum
            scale = "linear"
            label = name
            
        parameters[name] = {
            "min":min_,
            "max":max_,
            "step":(max_ - min_)/NSTEPS,
            "value":(max_+min_)/2,
            "scale":scale,
            "label":label
        }
    
    parameters["frequency"] = {
        "min" : 8,
        "max" : 18,
        "step": 0.1,
        "value": 14,
        "scale":"log",
        "label":"log10(frequency)"
    }

    parameters["max_phase"] = {
        "min":0,
        "max":6,
        "step":0.1,
        "value":1.5,
        "scale":"log",
        "label":"max log10(phase)"
    }

    parameters["min_phase"] = {
        "min":-6,
        "max":-0.1,
        "step":0.1,
        "value":-2,
        "scale":"log",
        "label":"min log10(phase)"
    }
    
    return model_dict[model_name], parameters
            
@ui.refreshable
def display_object_list(model_list:list[str]):
    """Displays a scrollable area of the object default names in object_list"""
    with ui.scroll_area():
        ui.radio(
            model_list,
            on_change = lambda e : add_dynamic_plotly_controls.refresh(e.value)
        )

@ui.refreshable
def add_dynamic_plotly_controls(model_name):
    """
    Generic helper to add parameter sliders and plot
    
    Args:
        compute_func: Function that takes **params and returns (x, y)
        parameters: Dict of {param_name: {min, max, step, value}}
    """

    compute_func, parameters = _get_model_parameters(model_name)
    if compute_func is None:
        return

    ui.label(model_name+":").classes("text-h4")
    
    with ui.grid(columns=4).classes('w-full'):

        with ui.column().classes("align-left col-span-3"):
            plot = ui.plotly({})
        params_dict = {}

        def update():
            min_time = np.log10(params_dict["min_phase"])
            max_time = np.log10(params_dict["max_phase"])
            
            times = np.logspace(min_time, max_time, 1_000)
            flux = compute_func(times, output_format="flux_density", **params_dict)
            fig = go.Figure(data=[go.Scatter(x=times, y=flux, mode='lines')])
            fig.update_layout(
                height=500,
                xaxis_title = "Phase (days)",
                yaxis_title = "Flux Density (mJy)",
            )
            fig.update_xaxes(type="log")
            fig.update_yaxes(type="log")
            plot.figure = fig
            plot.update()

        with ui.card():
            for param_name, config in parameters.items():

                scale = config.pop("scale")
                label = config.pop("label")

                ui.label(label+":")
                slider = ui.slider(**config).props('label-always')
                slider.on_value_change(
                    lambda p=param_name, s=slider: (
                        params_dict.update({p: s.value}) if scale=="linear"
                        else params_dict.update({p: 10**s.value}),
                        update()
                    )
                )
                if scale == "linear":
                    params_dict[param_name] = config['value']
                else:
                    params_dict[param_name] = 10**config['value']
    update()    
