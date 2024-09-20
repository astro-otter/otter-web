import os
tmpdir = "src/otter_web/tmp"
if not os.path.exists(tmpdir):
    os.mkdir(tmpdir)

from nicegui import ui, app
from otter_web.client import *
from otter_web.config import *

ui.run(
    title = 'OTTER', # sets the title of the tab
    favicon = 'src/otter_web/static/logo.png',
    dark = None, # inherits dark mode from the computer settings
    storage_secret = storage_secret
)
