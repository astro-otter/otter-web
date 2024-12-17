import os
import argparse

tmpdir = "src/otter_web/tmp"
if not os.path.exists(tmpdir):
    os.mkdir(tmpdir)

from nicegui import ui, app
from otter_web.client import *
from otter_web.config import *


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--on-air",
        help="use the on_air feature of NiceGUI",
        action=argparse.BooleanOptionalAction
    )
    args = parser.parse_args()

    if args.on_air:
        args.on_air = os.environ.get("NICEGUI_ON_AIR_TOKEN", True)

    ui.run(
        title = 'OTTER', # sets the title of the tab
        favicon = 'src/otter_web/static/logo.png',
        dark = None, # inherits dark mode from the computer settings
        storage_secret = storage_secret,
        on_air = args.on_air
    )

if __name__ in {"__main__", "__mp_main__"}:
    main()
