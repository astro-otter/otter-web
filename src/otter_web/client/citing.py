import os
import numpy as np
import ads
import logging

from nicegui import ui, app
from ..theme import frame
from ..config import API_URL, WEB_BASE_URL
from .search_util import SearchInput

from otter import Otter, Transient

logger = logging.getLogger(__name__)
db = Otter(url=API_URL)

OTTER_BIBTEX = """
@ARTICLE{2026ApJ...999..243F,
       author = {{Franz}, Noah and {Alexander}, Kate D. and {Gomez}, Sebastian and {Christy}, Collin T. and {Laskar}, Tanmoy and {van Velzen}, Sjoert and {Earl}, Nicholas and {Gezari}, Suvi and {Karmen}, Mitchell and {Margutti}, Raffaella and {Pearson}, Jeniveve and {Villar}, V. Ashley and {Zabludoff}, Ann I.},
        title = "{The Open mulTiwavelength Transient Event Repository (OTTER): Infrastructure Release and Tidal Disruption Event Catalog}",
      journal = {\apj},
     keywords = {Catalogs, Astronomy databases, Astronomy software, Transient sources, Tidal disruption, 205, 83, 1855, 1851, 1696},
         year = 2026,
        month = mar,
       volume = {999},
       number = {2},
          eid = {243},
        pages = {243},
          doi = {10.3847/1538-4357/ae346e},
       adsurl = {https://ui.adsabs.harvard.edu/abs/2026ApJ...999..243F},
      adsnote = {Provided by the SAO/NASA Astrophysics Data System}
}

@ARTICLE{2026JOSS...11.9516F,
       author = {{Franz}, Noah and {Alexander}, Kate and {Gomez}, Sebastian},
        title = "{A Python API for OTTER}",
      journal = {The Journal of Open Source Software},
     keywords = {Emacs Lisp, Lua, Python},
         year = 2026,
        month = feb,
       volume = {11},
       number = {118},
          eid = {9516},
        pages = {9516},
          doi = {10.21105/joss.09516},
       adsurl = {https://ui.adsabs.harvard.edu/abs/2026JOSS...11.9516F},
      adsnote = {Provided by the SAO/NASA Astrophysics Data System}
}
"""

@ui.page(os.path.join(WEB_BASE_URL, "citing"))
async def citing_us_page():

    app.storage.user.update(CHECKBOXES={})

    search_input = SearchInput()
    
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
* Please also include a citation to the OTTER catalog and API (see below).

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
            """The below form allows you to download the references associated with a given transient.
            After you press submit, it will download a bibtex file with all of the
            appropriate citations"""
        ).style("font-size:150%;")
        names = ui.input(
            'Transient Name',
            placeholder='Enter a transient name or partial name',
            on_change = search_input.add_name
        )
    
        ui.button(
            "Download Citations",
            on_click = lambda : ui.download(
                generate_bibtex_file(names=search_input.search_kwargs["names"]),
                "otter-citations.bib"
            )
        )
        
        ui.label(
            "Citation for the OTTER Catalog Paper"
        ).classes("text-h4")
        ui.code(OTTER_BIBTEX).classes("full-width")

def _get_all_refs(t):
    res = []
    for key in ["name/alias", "coordinate", "date_reference", "distance", "classification/value", "photometry", "host"]:
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
    
def generate_bibtex_file(names):

    ui.notification(
        "Generating the bibtex...",
        type="ongoing",
        timeout=None,
        spinner = True,
        close_button=True
    )

    transients = db.query(names=names)

    all_bibcodes = []    
    for t in transients:
        _, bibcodes = _get_all_refs(t)
        all_bibcodes += bibcodes

    all_bibcodes = np.unique(all_bibcodes)
    logger.info(all_bibcodes)
    try:
        bibtex = ads.ExportQuery(bibcodes=list(all_bibcodes)).execute()
    except ads.exceptions.APIResponseError as exc:
        ui.notify(f"""
        The ADS API responded with an error! We recommend limiting the number of
        citations you are attempting to download. The error message is: \n
        {exc}
        """,
        position="center",
        type="negative"
    )
        
    return (bibtex+OTTER_BIBTEX).encode("utf-8")
    
