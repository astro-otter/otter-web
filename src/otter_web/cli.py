import click
from nicegui import ui, app
from .pages import *
from pathlib import Path


@click.command()
def cli():
    app.add_static_files("/static", str(Path(__file__).parent / "static"))

    ui.run()
