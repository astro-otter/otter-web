import os

from nicegui import ui, context, background_tasks
from plotly import graph_objects as go
import numpy as np

import redback

from typing import Callable, Dict, Any
from ..config import API_URL, WEB_BASE_URL

@ui.page(os.path.join(WEB_BASE_URL, "redback_interactive"))
async def redback_plot():

    model_dict = redback.model_library.all_models_dict
    all_model_names = list(model_dict.keys())
    model_name = "arnett"

    priors = redback.priors.get_priors(model_name)

    parameters = {
        name : {
            "min": p.minimum,
            "max": p.maximum,
            "step": (p.maximum-p.minimum)/p.maximum,
            "value": p.minimum+(p.maximum-p.minimum)/p.maximum,
        } for name, p in priors.items()
    }
    parameters["frequency"] = {
        "min" : 8,
        "max" : 18,
        "step": 0.1,
        "value": 14
    }

    add_dynamic_plotly_controls(model_dict[model_name], parameters)

def add_dynamic_plotly_controls(
    compute_func: Callable,
    parameters: Dict[str, Dict[str, Any]]
):
    """
    Generic helper to add parameter sliders and plot
    
    Args:
        compute_func: Function that takes **params and returns (x, y)
        parameters: Dict of {param_name: {min, max, step, value}}
    """
    plot = ui.plotly({})
    params_dict = {}
    
    def update():
        times = np.logspace(-2, 2)
        flux = compute_func(times, output_format="flux_density", **params_dict)
        fig = go.Figure(data=[go.Scatter(x=times, y=flux, mode='markers')])
        fig.update_layout(height=500)
        plot.figure = fig
    
    with ui.card():
        for param_name, config in parameters.items():
            slider = ui.slider(
                min=config['min'],
                max=config['max'],
                step=config['step'],
                value=config['value'],
                #label=param_name
            )
            slider.on_value_change(
                lambda p=param_name, s=slider: (
                    params_dict.update({p: s.value}),
                    update()
                )
            )
            params_dict[param_name] = config['value']
    
    update()

    
    
