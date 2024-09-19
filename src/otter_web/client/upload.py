import io
import zipfile
import json
import re

import pandas as pd

from nicegui import ui
from ..theme import frame
from ..config import API_URL
from .home import post_table

from functools import partialmethod, partial
from dataclasses import dataclass

from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.time import Time

from validate_email import validate_email

from otter import Otter

db = Otter(url=API_URL)

class InvalidInputError(Exception):
    pass

@dataclass
class UploadInput:
    # uploader info
    uploader_name:str = None
    uploader_email:str = None

    # reference info
    bibcode: str = None

    # object metadata
    obj_name: str = None
    ra: str|float = None
    dec: str|float = None
    dec_unit: str = "deg"
    ra_unit: str = None

    redshift: float = None
    lum_dist: float = None
    lum_dist_unit: str = None
    comoving_dist: float = None
    comoving_dist_unit: str = None
    discovery_date: str = None
    discovery_date_format: str = None
    proposed_classification: str = None

    # photometry dataframe
    phot_df : pd.DataFrame = None

    # some useful methods
    def __setattr__(self, k, v):
        if v is None or isinstance(v, (str, pd.DataFrame)):
            super().__setattr__(k, v)
        else:
            super().__setattr__(k, v.value)
    
    def verify_input(self):

        # check that all required keys are provided
        required_keys = [
            "uploader_name",
            "uploader_email",
            "bibcode",
            "obj_name",
            "ra",
            "dec",
            "ra_unit",
            "dec_unit"
        ]
        required_vals = [getattr(self, k) for k in required_keys]

        if None in required_vals:
            for k, v in zip(required_keys, required_vals):
                if v is None:
                    ui.notify(f"{k.replace('_', ' ')} is required!")
            raise InvalidInputError()

        # check that conditional values are set
        if self.lum_dist is not None and self.lum_dist_unit is None:
            ui.notify(f"luminosity distance units are required if the luminosity distance is provided!")
            raise InvalidInputError()

        if self.comoving_dist is not None and self.comoving_dist_unit is None:
            ui.notify(f"comoving distance units are required if the comoving distance is provided!")
            raise InvalidInputError()

        if self.discovery_date is not None and self.discovery_date_format is None:
            ui.notify(f"Discovery date format is required if the discovery date is provided!")
            raise InvalidInputError()

        # check units
        try:
            u.Unit(self.ra_unit)
        except Exception as e:
            ui.notify("the provided ra unit is not a valid astropy unit")
            raise InvalidInputError() from e

        try:
            SkyCoord(self.ra, self.dec, unit=(self.ra_unit, self.dec_unit))
        except Exception as e:
            ui.notify("Astropy SkyCoord could not parse your ra, dec, and ra unit!")
            raise InvalidInputError() from e
            
        if self.lum_dist is not None:
            try:
                u.Unit(self.lum_dist_unit)
            except Exception as e:
                ui.notify("The provided luminosity distance unit is not a valid astropy unit")
                raise InvalidInputError() from e
        
        if self.comoving_dist is not None:
            try:
                u.Unit(self.comoving_dist_unit)
            except Exception as e:
                ui.notify("The provided comoving distance unit is not a valid astropy unit")
                raise InvalidInputError() from e
            
        if self.discovery_date is not None:
            try:
                Time(self.discovery_date, format=self.discovery_date_form)
            except Exception as e:
                ui.notify("The discovery date and discovery date format do not match astropy checking!")
                raise InvalidInputError() from e
                

        # check that the email address is at least syntactically correct
        is_valid_email = validate_email(
            email_address=self.uploader_email,
            check_format=True,
            check_blacklist=True,
            check_dns=True,
            dns_timeout=10,
            check_smtp=True,
            smtp_timeout=10,
            smtp_helo_host='my.host.name',
            smtp_from_address='my@from.addr.ess',
            smtp_skip_tls=False,
            smtp_tls_context=None,
            smtp_debug=False,
            # address_types=frozenset([IPv4Address, IPv6Address])
        )
        if not is_valid_email:
            ui.notify("The email address provided is not valid!")
            raise InvalidInputError()

def validate_and_save_phot(e, save_values):
    text = e.content.read().decode('utf-8')

    try:
        df = pd.read_csv(io.StringIO(text), sep=',')
    except Exception as e:
        ui.notify("Unable to finish your upload because pandas can't parse this file!")
        raise InvalidInputError()

    print(df)
    save_values("phot_df", df)
    
    
def add_to_otter(upload_input: UploadInput):
    upload_input.verify_input()
    print(str(upload_input))

def collect_uploader_info(set_values):

    ui.label("Uploader Information").classes("text-h5")
    ui.input("Name", on_change=partial(set_values, "uploader_name"))
    ui.input("Email Address", on_change=partial(set_values, "uploader_email"))

def collect_reference_info(set_values):

    ui.label("Citation Information").classes("text-h5")
    #ui.input("First Author", on_change=partial(set_values, "first_author"))
    #ui.number("Year Published", on_change=partial(set_values, "year"))
    #ui.input("Paper Title", on_change=partial(set_values, "title"))
    ui.input("ADS Bibcode", on_change=partial(set_values, "bibcode"))

def collect_photometry(set_values):

    phot_instructions = """
    Please upload your photometry file here and follow these instructions carefully.
    This should have the following required columns:

    * `name`: The same name that you put in your metadata file
    * `flux`: The flux, fluxdensity, or count rate of the point
    * `flux_unit`: The unit on the flux measurement
    * `date`: The date you took this flux measurement
    * `date_format`: The astropy time string format that you used for this date
    * `filter`: The name of the filter that you used to make this measurement

    Then there are some columns that are required in some cases:

    * `telescope_area`: Collecting area of the telescope. Required if the photometry is given in counts!
    * `min_energy`:
    * `max_energy`:
    * `val_k`: The k-correction value applied. Only required if a k-correction was applied.
    * `val_s`: The s-correction value applied. Required if an s-correction was applied.
    * `val_av`: The value of the applied Milky Way Extinction. Required if the photometry was corrected for Milky Way Extinction.
    * `val_host`: The value of the applied host correction. Required only if the photometry is host subtracted.
    * `val_hostav`: The value of the host extinction. Required if the photometry was corrected for host extinction.
    * `upperlimit`: Boolean. True if this is an upperlimit. In this case, the flux should be given as a 3-sigma upperlimit!

    Then the purely optional columns are:

    * `flux_err`: The error on the raw photometry value given.
    * `date_err`: The error on the date given. 
    * `sigma`: Significance of the upperlimit (if it is an upperlimit).
    * `instrument`: The instrument used to collect this data.
    * `phot_type`: is the photometry PSF, Aperature, or synthetic.
    * `exptime`: The exposure time
    * `aperature`: The aperature diameter in arcseconds, if aperature photometry.
    * `observer`: Name of the observer for this point.
    * `reducer`: Name of the person who reduced this data point.
    * `pipeline`: Name and version of the pipeline used to reduce this data.
    * `filter_eff`: The effective wavelength or frequency of the filter. We will use the filter_eff_units key to determine this. Please provide this if the filter you used in atypical or obscure, we have a lot of these values already stored but not all of them!
    * `filter_eff_units`: The units of filter_eff.
    * `telescope`: The name of the telescope or observatory. 
    """
    
    with ui.grid(columns=2):
        ui.label("Photometry File Upload").classes("text-h5")
        ui.button(
        "Download Sample Photometry File",
        on_click=lambda: ui.download("/static/sample_phot.csv")
    )
    
    ui.markdown(phot_instructions)
    ui.upload(
        auto_upload=True,
        on_upload=lambda e: validate_and_save_phot(e, set_values)
    ).classes("w-full")
    
def single_object_upload_form():

    uploaded_values = UploadInput()
    set_value = partial(setattr, uploaded_values)
    
    collect_uploader_info(set_value)
    collect_reference_info(set_value)

    # object information
    ui.label("Single Object Information").classes("text-h5")
    ui.label("Required Information").classes("text-h6")
    ui.input("Name", on_change=partial(set_value, "obj_name"))
    ui.input("RA", on_change=partial(set_value, "ra"))
    ui.input("Declination (Degrees)", on_change=partial(set_value, "dec"))
    
    unit_options = ['hourangle', 'degree']
    ui.select(
        unit_options,
        label = "RA Units",
        on_change = partial(set_value, "ra_unit")
    )

    ui.label("Optional Information (Only if YOU measured it)").classes("text-h6")
    ui.input("Redshift", on_change=partial(set_value, "redshift"))
    ui.input("Luminosity Distance", on_change=partial(set_value, "lum_dist"))
    ui.input("Luminosity Distance Astropy Unit String", on_change=partial(set_value, "lum_dist_unit"))
    ui.input("Comoving Distance", on_change=partial(set_value, "comoving_dist"))
    ui.input("Comoving Distance Astropy Unit String", on_change=partial(set_value, "comoving_dist_dist"))
    ui.input("Discovery Date", on_change=partial(set_value, "discovery_date"))
    ui.input("Discovery Date Astropy Format String", on_change=partial(set_value, "discovery_date_format"))
    ui.input("Classification", on_change=partial(set_value, "proposed_classification"))

    # photometry
    collect_photometry(set_value)

    ui.button('Submit').props('type="submit"').on_click(
        lambda: add_to_otter(
            uploaded_values
        )
    )     

    
def multi_object_upload_form():

    collect_uploader_info()
    collect_reference_info()
    
# Function to switch between forms
def show_form(selected_form, containers=None):
    if containers is not None:
        for val in list(containers)[1:]:
            val.delete()
    if selected_form == 'Single Object':
        single_object_upload_form()
    elif selected_form == 'Multiple Objects':
        multi_object_upload_form()
        
@ui.page("/upload")
async def upload():

    partial_show_form = partial(show_form)
    
    with frame():

        ui.label("Upload Data to OTTER").classes("col-span-5 text-h4")
            
        # Display the initial
        with ui.grid(rows="auto auto").classes("w-full") as grid:
            selected_tab = ui.toggle(
                ['Single Object', 'Multiple Objects'],
                value='Single Object',
                on_change=lambda e: partial_show_form(e.value, containers=grid)
            ).style("width: 26.25%")
            
            partial_show_form(selected_tab.value)
