from nicegui import ui, app
from otter_web.client import *

ui.run(
    title = 'OTTER', # sets the title of the tab
    favicon = 'src/otter_web/static/logo.png',
    dark = None, # inherits dark mode from the computer settings
)
