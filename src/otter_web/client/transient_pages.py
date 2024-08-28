from nicegui import ui

@ui.page('/transient/{transient_default_name}')
def transient_subpage(transient_default_name:str):
    ui.label(f'Welcome to the page for {transient_default_name}!')
