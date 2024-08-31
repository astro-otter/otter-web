from nicegui import ui
from ..theme import frame

@ui.page("/upload")
async def upload():
    with frame():
        ui.label("Data upload form is coming soon...").classes("text-h4")
