import numpy as np
import ads

from nicegui import ui
from ..theme import frame
from ..config import API_URL

from otter import Otter, Transient

db = Otter(url=API_URL)

CHECKBOXES = {}

@ui.page("/citing")
async def citing_us_page():

    with frame():
        imsize=32
        with ui.grid(rows=1, columns=16).classes("gap-0 no-wrap"):                        

            ui.image(
                "src/otter_web/static/logo.png"
            ).classes(f"w-{imsize} col-span-4")

            ui.label(
                "Citing the OTTER Catalog"
            ).classes("text-h2 col-span-12")

        ui.markdown("""
OTTER is an open source, public catalog and is supposed to make it easy to use published
data. That being said, we expect others to use the data for their research papers.
However, we expect that the data is properly cited according to the following
citation policy:
        
* The original source of all of the data you use is properly cited. An example is, if
  you use the radio data on the TDE SwJ1644+57, you should cite the original series of
  papers on the radio evolution of SwJ1644+57: Berger et al. (2012), Zauderer et al.
  (2013), Zauderer et al. (2011), Eftekhari et al. (2018), Cendes, Y. et al. (2021).
* Please also include a citation to the OTTER catalog (see below).

If you use the OTTER infrastructure in your research in any way, please follow the
citation policy described above. We have attempted to make this as painless as possible
when you use the form below. It will give you a bibtex file with all of the citations
associated with each object you select.
        
If (When?) you upload your data to OTTER to make it publicly available and easy to use
after publishing, please add a citation to OTTER to your paper when describing *how*
you are making it public.

_Disclaimer:_ We have done our best include every possible citation. But, as you can imagine, this is an extremely difficult task and we will inevitably make mistakes and miss papers. If you don't see a paper cited in OTTER, please reach out the developers and they will see to it that it gets appropriately added!
        """).style("font-size:150%;")

        ui.label(
            "Retrieve Citations"
        ).classes("text-h4")
        ui.markdown(
            """The below form allows you to select all of the objects you wish to cite.
            After you press submit, it will download a bibtex file with all of the
            appropriate citations"""
        ).style("font-size:150%;")

        ui.input(
            label="Object Name",
            on_change=lambda e : display_object_list.refresh(
                db.get_meta(
                    names=e.value
                )
            )
        )
        display_object_list(db.get_meta())
        ui.button(
            "Download Citations",
            on_click = lambda : ui.download(
                generate_bibtex_file(),
                "otter-citations.bib"
            )
        )
        
        ui.label(
            "Citation for the OTTER Catalog Paper"
        ).classes("text-h4")
        ui.code(
	  "INSERT CITATION HERE ONCE THE CATALOG IS PUBLISHED"
        ).classes("full-width")

@ui.refreshable    
def display_object_list(object_list:list[Transient]):
    """Displays a scrollable area of the object default names in object_list"""
    global CHECKBOXES;
    with ui.scroll_area():
        with ui.grid(columns=4):
            for t in object_list:
                checkbox = ui.checkbox(
                    CHECKBOXES[t.default_name].text  if t.default_name in CHECKBOXES else t.default_name,
                    on_change = lambda e : _toggle_checkbox(e),
                    value = CHECKBOXES[t.default_name].value if t.default_name in CHECKBOXES else False
                )
                            
def _toggle_checkbox(e):
    global CHECKBOXES
    CHECKBOXES[e.sender.text] = e.sender

def _get_all_refs(t):
    res = []
    for key in ["name/alias", "coordinate", "date_reference", "distance", "classification", "photometry", "host"]:
        if key not in t: continue
        details = t[key]
        for d in details:
            refs = d['reference']
            if isinstance(refs, list):
                res += refs
            elif isinstance(refs, str):
                res.append(refs)
            else:
                raise ValueError(f"{refs} is an unexpected format!")
    uq_refs = np.unique(res)
    
    uq_refs = [ref for ref in uq_refs if len(ref) == 19]
    
    tocite = ' '.join([f"{{\citet{{{r.strip()}}}}}" for r in uq_refs])
    return tocite, [r.strip() for r in uq_refs]
    
def generate_bibtex_file():
    global CHECKBOXES

    bibstr_list = []
    names = [checkbox.text for checkbox in CHECKBOXES.values()]
    transients = db.query(names=names)

    all_bibcodes = []    
    for t in transients:
        _, bibcodes = _get_all_refs(t)
        all_bibcodes += bibcodes

    all_bibcodes = np.unique(all_bibcodes)
    bibtex = ads.ExportQuery(bibcodes=list(all_bibcodes)).execute()
        
    return bibtex.encode("utf-8")
    
