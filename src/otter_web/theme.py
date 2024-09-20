from contextlib import contextmanager
from pathlib import Path
from nicegui import ui, app

@contextmanager
def frame(drawer=None):
    dark = ui.dark_mode()
    ui.query("body").style(
        "font-family: 'Inter var', -apple-system, BlinkMacSystemFont, Segoe UI, "
        "Roboto, Helvetica, Arial, sans-serif, Apple Color Emoji, "
        "Segoe UI Emoji, Segoe UI Symbol"
    )
    ui.query(".body--light").style(f"background-color: #eff3f8")

    def _toggle_dark(*args):
        dark.toggle()

        if dark.value:
            ui.query(".body--dark").style(f"background-color: #121212")
            footer.classes(remove="text-dark", add="text-white")
        else:
            ui.query(".body--light").style(f"background-color: #eff3f8")
            footer.classes(remove="text-white", add="text-dark")

    with ui.header(elevated=False).classes("q-pa-none"):
        with ui.element("q-toolbar").classes("bg-primary text-white"):
            # with ui.element("q-img"):
            with ui.element("q-toolbar-title").style(
                f"width: {'246px' if drawer is not None else '150px'}; flex: none"
            ):
                ui.image(source="/static/logo.png").classes("text-white").style(
                    "width: 50px; margin:5px"
                )
                ui.link("OTTER", "/").classes(replace="").style(
                    "font-weight: bold; padding-left: 5px"
                )

            if drawer is not None:
                ui.button(on_click=drawer.toggle).props(
                    "flat round dense icon=menu"
                ).classes("text-white q-mr-sm")

                ui.separator().props("dark vertical inset").classes("q-mr-sm")

            with ui.button().props("flat").classes("text-white"):
                ui.link("Catalog", "/").classes(replace="")

            with ui.button().props("flat").classes("text-white"):
                ui.link("Search", "/search").classes(replace="")

            with ui.button().props("flat").classes("text-white"):
                ui.link("Upload Data", "/upload").classes(replace="")
                
            with ui.button().props("flat").classes("text-white"):
                ui.link(
                    "Documentation", "https://astro-otter.readthedocs.io"
                ).classes(replace="")
    
            ui.element("q-space")

            #with ui.button().props("flat").classes("text-white"):
            #    ui.link("Log in", "/").classes(replace="")

            #with ui.button().props("flat").classes("text-white"):
            #    ui.link("Register", "/").classes(replace="")

            ui.separator().props("dark vertical inset").classes("q-mx-sm")

            ui.button(on_click=_toggle_dark).props(
                "flat round dense icon=dark_mode"
            ).classes("text-white")

    with ui.footer(fixed=False).classes(
        "transparent text-dark border-t flex-center"
    ) as footer:  # "transparent border-t text-dark q-px-md q-mx-md"):
        ui.label("Copyright OTTER 2024")

    with ui.column().classes("w-full p-8 lg:p-16 max-w-[1250px] mx-auto"):
        yield
