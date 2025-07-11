import os
import io
import zipfile
import json
import re
import email
import smtplib
import uuid
import logging
import traceback
import shutil
import asyncio
import time

import pandas as pd

from nicegui import ui, app, background_tasks, run 
from ..theme import frame
from ..config import API_URL, vetting_password, WEB_BASE_URL

from functools import partialmethod, partial
from dataclasses import dataclass

from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.time import Time

from validate_email import validate_email

from otter import Otter

log = logging.getLogger("otter-log")

db = Otter(url=API_URL, username="vetting-user", password=vetting_password)

class InvalidInputError(Exception):
    def __init__(self, msg, type=None):
        super().__init__(msg)

class BackgroundTaskStack(list):
    pass

@dataclass
class UploadInput:
    # uploader info
    uploader_name:str = None
    uploader_email:str = None

    # object metadata
    obj_name: str = None
    ra: str|float = None
    dec: str|float = None
    dec_unit: str = "deg"
    ra_unit: str = None
    coord_bibcode: str = None
    
    redshift: float = None
    redshift_bibcode: str = None
    lum_dist: float = None
    lum_dist_unit: str = None
    lum_dist_bibcode: str = None
    comoving_dist: float = None
    comoving_dist_unit: str = None
    comoving_dist_bibcode: str = None
    discovery_date: str = None
    discovery_date_format: str = None
    discovery_date_bibcode: str = None
    proposed_classification: str = None
    classification_flag: str = None
    classification_bibcode: str = None

    # photometry dataframe
    phot_df : pd.DataFrame = None
    meta_df : pd.DataFrame = None
    
    # some useful methods
    def __setattr__(self, k, v):
        if v is None or isinstance(v, (str, pd.DataFrame)):
            super().__setattr__(k, v)
        else:
            super().__setattr__(k, v.value)
    
    def verify_input(self, _validate_email=False):

        # check that all required keys are provided
        required_keys = [
            "uploader_name",
            "uploader_email",
            "obj_name",
            "ra",
            "dec",
            "ra_unit",
            "dec_unit",
            "coord_bibcode"
        ]
        required_vals = [getattr(self, k) for k in required_keys]

        if None in required_vals:
            msg = ""
            for k, v in zip(required_keys, required_vals):
                if v is None:
                    msg+=f"{k.replace('_', ' ')} is required!\n"
            raise InvalidInputError(msg)

        # check that conditional values are set
        if self.lum_dist is not None and (self.lum_dist_unit is None or self.lum_dist_bibcode is None):
            raise InvalidInputError(f"luminosity distance units and bibcode are required if the luminosity distance is provided!", type="negative")

        if self.comoving_dist is not None and (self.comoving_dist_unit is None or self.comoving_dist_bibcode is None):
            raise InvalidInputError(f"comoving distance units are required if the comoving distance is provided!", type="negative")
          
        if self.discovery_date is not None and (self.discovery_date_format is None or self.discovery_date_bibcode is None):
            raise InvalidInputError(f"Discovery date format is required if the discovery date is provided!", type="negative")
            
        # check units
        try:
            u.Unit(self.ra_unit)
        except Exception as e:
            raise InvalidInputError("the provided ra unit is not a valid astropy unit") from e

        try:
            SkyCoord(self.ra, self.dec, unit=(self.ra_unit, self.dec_unit))
        except Exception as e:
            raise InvalidInputError("Astropy SkyCoord could not parse your ra, dec, and ra unit!", type="negative") from e
            
        if self.lum_dist is not None:
            try:
                u.Unit(self.lum_dist_unit)
            except Exception as e:
                raise InvalidInputError("The provided luminosity distance unit is not a valid astropy unit") from e
        
        if self.comoving_dist is not None:
            try:
                u.Unit(self.comoving_dist_unit)
            except Exception as e:
                raise InvalidInputError("The provided comoving distance unit is not a valid astropy unit") from e
            
        if self.discovery_date is not None:
            try:
                Time(self.discovery_date, format=self.discovery_date_form)
            except Exception as e:
                raise InvalidInputError("The discovery date and discovery date format do not match astropy checking!") from e
                
        
        # check that the email address is at least syntactically correct
        if _validate_email:
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
            if self.uploader_email[-4:] != ".edu" and not is_valid_email:
                raise InvalidInputError("The email address provided is not valid!", type="negative")

def validate_and_save_phot(e, save_values):
    text = e.content.read().decode('utf-8')

    try:
        df = pd.read_csv(io.StringIO(text), sep=',')
    except Exception as exc:
        e.sender.reset()
        ui.notify("Unable to finish your upload because pandas can't parse this file!")
        raise InvalidInputError() from exc

    # drop rows that are entirely blank (this can happen when exporting csvs from excel
    # and google sheets)
    df = df.dropna(how="all")
    
    # make sure all of the required columns are there
    required_columns = [
        "name",
        "bibcode",
        "flux",
        "flux_err",
        "flux_unit",
        "date",
        "date_format",
        "filter",
        "filter_eff",
        "filter_eff_units"
    ]
    df.columns = [c.strip() for c in list(df.columns)]
    atleast_one_missing = False
    for col in required_columns:
        if col not in df.columns:
            ui.notify(f"{col} is required and is missing from your photometry file!", type='negative')
            atleast_one_missing = True

    if atleast_one_missing:
        e.sender.reset()
        raise InvalidInputError()

    # then also check some of the formats of the required columns
    for date, date_format in zip(df.date, df.date_format):
        try:
            Time(date, format=date_format)
        except Exception as exc:
            ui.notify("At least one of the dates you provided for the photometry does not match the format given in the date_format column!", type="negative")
            e.sender.reset()
            raise InvalidInputError("At least one of the dates you provided for the photometry does not match the format given in the date_format column!") from exc
            
    save_values("phot_df", df)

def validate_and_save_meta(e, save_values):

    text = e.content.read().decode('utf-8')

    try:
        df = pd.read_csv(io.StringIO(text), sep=',')
    except Exception as exc:
        ui.notify("Unable to finish your upload because pandas can't parse this file!")
        e.sender.reset()
        raise InvalidInputError() from exc

    # drop rows that are entirely blank (this can happen when exporting csvs from excel
    # and google sheets)
    df = df.dropna(how="all")
    
    required_columns = [
        "name",
        "ra",
        "dec",
        "ra_unit",
        "dec_unit",
        "coord_bibcode"
    ]

    df.columns = [c.strip() for c in list(df.columns)]
    atleast_one_missing = False
    for col in required_columns:
        if col not in df.columns:
            ui.notify(f"{col} is required and is missing from your photometry file!", type='negative')
            atleast_one_missing = True

    if atleast_one_missing:
        e.sender.reset()
        raise InvalidInputError()

    save_values("meta_df", df)
    
async def send_to_vetting(upload_input: UploadInput, input_type:str, outpath:str):

    # await asyncio.sleep(10)

    log.debug("Saving the original input csvs to a tmp directory")
    metapath = os.path.join(outpath, "meta.csv")
    photpath = os.path.join(outpath, "photometry.csv")
    if upload_input.phot_df is not None:
        upload_input.phot_df.to_csv(photpath)
    upload_input.meta_df.to_csv(metapath)
    
    # upload the data to the otter vetting collection
    log.debug("Connecting to the database and uploading the data to the vetting collection")
    try:
        local_db = Otter.from_csvs(
            metafile = metapath,
            photfile = photpath if os.path.exists(photpath) else None,
            local_outpath = outpath,
            db = db
        )
        local_db.upload_private(collection="vetting", testing=False)
    except Exception as e:
        log.exception(f"""
        Upload failed with exception {e}! Please try again or contact an OTTER admin!
        """)
        raise InvalidInputError(f"Upload failed: {e}")
        
async def redirect_and_send_to_vetting(
        upload_input: UploadInput,
        task_stack : BackgroundTaskStack,
        input_type
):
    
    if input_type == "single":
        log.debug("processing the single upload form input into a dataframe...")
        log.debug("Verifying input...")
        upload_input.verify_input()
        log.debug("Input verification succeeded!")

        meta_dict = dict(
            name = [upload_input.obj_name],
            ra = [upload_input.ra],
            dec = [upload_input.dec],
            ra_unit = [upload_input.ra_unit],
            dec_unit = [upload_input.dec_unit],
            coord_bibcode = [upload_input.coord_bibcode]
        )

        if upload_input.redshift is not None:
            meta_dict["redshift"] = [int(upload_input.redshift)]
            meta_dict["redshift_bibcode"] = [str(upload_input.redshift_bibcode)]

        if upload_input.lum_dist is not None:
            meta_dict["luminosity_distance"] = [int(upload_input.lum_dist)]
            meta_dict["luminosity_distance_unit"] = [upload_input.lum_dist_unit]
            meta_dict["luminosity_distance_bibcode"] = [str(upload_input.lum_dist_bibcode)]

        if upload_input.comoving_dist is not None:
            meta_dict["comoving_distance"] = [upload_input.comoving_dist]
            meta_dict["comoving_distance_units"] = [upload_input.comoving_dist_unit]
            meta_dict["comoving_distance_bibcode"] = [str(upload_input.comoving_dist_bibcode)]
            
        if upload_input.discovery_date is not None:
            meta_dict["discovery_date"] = [upload_input.discovery_date]
            meta_dict["discovery_date_format"] = [upload_input.discovery_date_format]
            meta_dict["discovery_date_bibcode"] = [str(upload_input.discovery_date_bibcode)]

        if upload_input.proposed_classification is not None:
            meta_dict["classification"] = [upload_input.proposed_classification]
            meta_dict["classification_flag"]= [
                upload_input.classification_flag if upload_input.classification_flag is not None else 0
            ]
            meta_dict["classification_bibcode"] = [str(upload_input.classification_bibcode)]

        upload_input.meta_df = pd.DataFrame(meta_dict)
        log.debug("finished processing the single input form data!")
    
    # add the uploader and email as comments to the meta_df
    log.debug("adding the uploader information to the metadata dataframe as a comment")
    upload_input.meta_df["comment"] = \
        f"Uploader:{upload_input.uploader_name} | Email:{upload_input.uploader_email}"
        
    # save the uploaded dataframes in the users storage
    log.debug("saving the dataframes to the users app storage")
    user_data = {
        "meta_df" : upload_input.meta_df.to_dict(),
    }
    if upload_input.phot_df is not None:
        user_data["phot_df"] = upload_input.phot_df.to_dict() 
    
    dataset_id = str(uuid.uuid4())
    outpath = os.path.join("/tmp", "otter", f"{dataset_id}")
    if not os.path.exists(outpath):
        os.makedirs(outpath)

    log.debug("starting the upload as a background task!")
    #task = background_tasks.create(send_to_vetting(upload_input, input_type, outpath))
    #task_stack.append(task) # this saves it to our stack
    try:
        await asyncio.wait_for(send_to_vetting(upload_input, input_type, outpath), timeout=119)
    except asyncio.TimeoutError as e:
        log.exception(f"Upload timed out: {e}")
        ui.notify(
            "Upload timed out after waiting for two minutes. Please check your dataset. If this dataset is particularly large and you suspect that is why it timed out, please contact an admin."
        )
        raise asyncio.TimeoutError()
        
    return dataset_id, user_data
    
def collect_uploader_info(set_values):

    ui.label("Uploader Information").classes("text-h5")
    ui.input("Name*", on_change=partial(set_values, "uploader_name"))
    ui.input("Email Address*", on_change=partial(set_values, "uploader_email"))

def collect_meta(set_values):
    meta_instructions = """
    Please upload your metadata file here. This should have the following required columns:

    * `name`: The TDE name, can be TNS or internal
    * `ra`: The RA of the TDE
    * `dec`: The dec of the TDE
    * `ra_unit`: astropy unit string format of the ra
    * `dec_unit`: astropy unit string format of the dec
    * `coord_bibcode`: The ADS bibcode associated with the coordinates you are uploading for this object

    Then there are some other optional column keys, please only provide these if you are the one who measured it since your publication will be associated with the measurement in the catalog!

    * `redshift`: The redshift of the TDE
    * `redshift_bibcode`: The bibcode associated with the redshift you are providing
    * `luminosity_distance`: The luminosity distance to the TDE
    * `luminosity_distance_unit`: The luminosity distance units required if you give us a luminosity distance
    * `luminosity_distance_bibcode`: The bibcode associated with the luminosity distance you are providing
    * `comoving_distance`: The comoving distance to the TDE
    * `comoving_distance_units`: The comoving distance units, required if you give us a comoving distance
    * `comoving_distance_bibcode`: The bibcode associated with the comoving distance you are providing
    * `discovery_date`: The date you discovered the object
    * `discovery_date_format`: astropy time string format of the discovery date, required if you provide a discovery date
    * `discovery_date_bibcode`: The bibcode associated with the discovery date you are providing
    * `classification`: What would you classify this transient as?
    * `classification_flag`: The flag for this classification. 0 means you don't trust the classification, 1 means it is photometrically classified, 2 means this is a TNS classificatin, and 3 means this is a spectroscopic classification.
    * `classification_bibcode`: The bibcode associated with the classification of this transient
    """

    with ui.grid(columns=2):
        ui.label("Metadata File Upload").classes("text-h5")
        ui.button(
        "Download Sample Metadata File",
        on_click=lambda: ui.download("/static/sample_meta.csv")
    )
    
    ui.markdown(meta_instructions)
    ui.upload(
        auto_upload=True,
        on_upload=lambda e: validate_and_save_meta(e, set_values)
    ).classes("w-full")
    
def collect_photometry(set_values):

    phot_instructions = """
    Please upload your photometry file here and follow these instructions carefully.
    Any null or NaN values should be filled with "NaN" to work with NumPy/Pandas. Values
    like "---" will not work.
    
    The photometry csv file should have the following required columns:

    * `name`: The same name that you put in your metadata file
    * `bibcode`: The ADS bibcode associated with your publication of this photometry
    * `flux`: The flux, flux density, or magnitude. If you are uploading counts, see the `raw` keyword below, which needs to be provided along with this. If the `raw` keyword is also used, this will be treated as a value after reduction (i.e. going into the `value` keyword in the schema). If this column is provided and not `raw`, it will be treated as the default raw value for this photometry point. 
    * `flux_err`: The error on the photometry value given. If the uncertainties are uneven, make this the mean of the upper and lower errors and add the upper and lower errors using the `upper_err` and `lower_err` columns, respectively (see below).
    * `flux_unit`: The unit on the flux measurement.
    * `date`: The date you took this flux measurement
    * `date_format`: The astropy time string format that you used for this date
    * `filter`: The name of the filter that you used to make this measurement. This must be unique with filter_eff. So, for example, you can not have multiple "r" filters with different filter_eff. We generally suggest dealing with this by naming your filters <filter_name>.<telescope_name>, for example "r.ztf".
    * `filter_eff`: The effective wavelength or frequency of the filter. We will use the filter_eff_units key to determine this.
    * `filter_eff_units`: The units of filter_eff.
    
    Then there are some columns that are required in some cases:

    * `telescope`: Telescope used to take the data. Required if the photometry is X-ray data!
    * `filter_min`: Minimum frequency or wavelength of the filter used. Required for X-ray data!
    * `filter_max`: Maximum frequency or wavelength of the filter used. Required for X-ray data!
    * `xray_model_name`: A colloquial name for the xray model that was applied to extract fluxes from this data.
    * `xray_model_param_value::<param_name>`: A special keyword for defining the best fit value for an X-ray model parameter. There can be an arbitrary number of these, but there should be one for each xray model parameter. Every one of these should start with the prefix `xray_model_param_value::`, then after the double colon (`::`), you should insert the name of the parameter (replacing `<param_name>` above). For example, for an absorbed powerlaw there would be two of these like `xray_model_param_value::N_H` and `xray_model_param_value::Gamma`.
    * `xray_model_param_up_err::<param_name>`: The same as `xray_model_param_value::<param_name>` but for the upper error on the best fit value. There should be the same number of these as there are `xray_model_param_value::<param_name>`!
    * `xray_model_param_lo_err::<param_name>`: The same as `xray_model_param_value::<param_name>` but for the upper error on the best fit value. There should be the same number of these as there are `xray_model_param_value::<param_name>`!
    * `xray_model_param_upperlimit::<param_name>`: The same as `xray_model_param_value::<param_name>` but a boolean that is set to True if the parameter value was an upperlimit, or False if not. There should be the same number of these as there are `xray_model_param_value::<param_name>`!
    * `xray_model_param_unit::<param_name>`: The same as `xray_model_param_value::<param_name>` but a string of the units for the model parameter. There should be the same number of these as there are `xray_model_param_value::<param_name>`!
    * `val_k`: The k-correction value applied. Only required if a k-correction was applied.
    * `val_s`: The s-correction value applied. Required if an s-correction was applied.
    * `val_av`: The value of the applied Milky Way Extinction. Required if the photometry was corrected for Milky Way Extinction.
    * `val_host`: The value of the applied host correction. Required only if the photometry is host subtracted.
    * `val_hostav`: The value of the host extinction. Required if the photometry was corrected for host extinction.
    * `upperlimit`: Boolean. True if this is an upperlimit. In this case, the flux should be given as a 3-sigma upperlimit!
    * `raw`: The raw counts from the telescope, this is mostly only used for X-ray data.
    * `raw_err`: The error on the raw counts from the telescope.
    * `raw_units`: The units on the raw counts from the telescope (probably `ct`).
    
    Then the purely optional columns are:

    * `date_err`: The error on the date given.
    * `date_min`: The first observation date for when observations have been binned. If provided, `date_max` is required.
    * `date_max`: The last observation date for when observations have been binned. If provided, `date_min` is required.
    * `sigma`: Significance of the upperlimit (if it is an upperlimit).
    * `instrument`: The instrument used to collect this data.
    * `phot_type`: is the photometry PSF, Aperature, or synthetic.
    * `exptime`: The exposure time
    * `aperature`: The aperature diameter in arcseconds, if aperature photometry.
    * `observer`: Name of the observer for this point.
    * `reducer`: Name of the person who reduced this data point.
    * `pipeline`: Name and version of the pipeline used to reduce this data.
    * `statistical_err`: The statistical error on the flux value.
    * `systematic_err`: The systematic error on the flux value.
    * `iss_err`: Any uncertainties associated with interstellar scintillation.
    * `upper_err`: The upper error, if the flux errors are uneven.
    * `lower_err`: The lower error, if the flux errors are uneven.
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
    
def single_object_upload_form(uploaded_values, tasks):

    set_value = partial(setattr, uploaded_values)
    
    collect_uploader_info(set_value)

    # object information
    ui.label("Single Object Information").classes("text-h5")
    ui.label("Required Information").classes("text-h6")
    ui.input("Name*", on_change=partial(set_value, "obj_name"))
    ui.input("RA*", on_change=partial(set_value, "ra"))
    ui.input("Declination (Degrees)*", on_change=partial(set_value, "dec"))
    
    unit_options = ['hourangle', 'degree']
    ui.select(
        unit_options,
        label = "RA Units*",
        on_change = partial(set_value, "ra_unit")
    )
    ui.input("Coordinate Bibcode*", on_change=partial(set_value, "coord_bibcode"))
    
    
    ui.label("Optional Information (Remember to cite the original source as the bibcode!)").classes("text-h6")
    ui.input("Redshift", on_change=partial(set_value, "redshift"))
    ui.input("Redshift Bibcode", on_change=partial(set_value, "redshift_bibcode"))
    
    ui.input("Luminosity Distance", on_change=partial(set_value, "lum_dist"))
    ui.input("Luminosity Distance Astropy Unit String", on_change=partial(set_value, "lum_dist_unit"))
    ui.input("Luminosity Distance Bibcode", on_change=partial(set_value, "lum_dist_bibcode"))

    ui.input("Comoving Distance", on_change=partial(set_value, "comoving_dist"))
    ui.input("Comoving Distance Astropy Unit String", on_change=partial(set_value, "comoving_dist_dist"))
    ui.input("Comoving Distance Bibcode", on_change=partial(set_value, "comoving_dist_bibcode"))

    ui.input("Discovery Date", on_change=partial(set_value, "discovery_date"))
    ui.input("Discovery Date Astropy Format String", on_change=partial(set_value, "discovery_date_format"))
    ui.input("Discovery Date Bibcode", on_change=partial(set_value, "discovery_date_bibcode"))

    ui.input("Classification", on_change=partial(set_value, "proposed_classification"))
    ui.input("Classification Flag", on_change=partial(set_value, "classification_flag"))
    ui.input("Classification Bibcode", on_change=partial(set_value, "classification_bibcode"))
    
    # photometry
    collect_photometry(set_value)

    return uploaded_values
    
def multi_object_upload_form(uploaded_values, tasks):

    set_value = partial(setattr, uploaded_values)

    collect_uploader_info(set_value)
    collect_meta(set_value)
    collect_photometry(set_value)

    return uploaded_values
    
# Function to switch between forms
async def _send_single_to_vetting(uploaded_values, tasks):
    note = ui.notification(
        "Uploading. This may take up to 2 minutes. Please do not refresh the page.",
        type="ongoing",
        timeout=None,
        spinner=True,
        close_button=True
    )

    await asyncio.sleep(0)
    
    try:
        dataset_id, res = await redirect_and_send_to_vetting(
            uploaded_values,
            tasks,
            input_type="single"
        )
        app.storage.user.update(data=res)
    
    except Exception as e:
        note.type="negative"
        note.message="Upload Failed!"
        ui.notify(e, type="negative", multi_line=True)
        log.error(e)
        return

    note.type="positive"
    note.message="Upload Done! Redirecting..."
    log.debug("navigating to the success page")
    ui.navigate.to(os.path.join(WEB_BASE_URL, f"upload", f"{dataset_id}", "success"))
        
async def _multi_send_to_vetting(uploaded_values, tasks):
    note = ui.notification(
        "Uploading. This may take up to 2 minutes. Please do not refresh the page.",
        type="ongoing",
        timeout=None,
        spinner=True,
        close_button=True
    )
    
    await asyncio.sleep(0)

    try:
        dataset_id, res = await redirect_and_send_to_vetting(
            uploaded_values,
            tasks,
            input_type="multi"
        )
        app.storage.user.update(data=res)
        
    except Exception as e:
        note.type="negative"
        note.message="Upload Failed!"
        ui.notify(e)
        log.error(e)
        return

    note.type="positive"
    note.message="Upload Done! Redirecting..."
    log.debug("navigating to the success page")
    ui.navigate.to(os.path.join(WEB_BASE_URL, f"upload", f"{dataset_id}", "success"))
    
def show_form(selected_form, tasks, containers=None):

    uploaded_values = UploadInput()
    
    if containers is not None:
        for val in list(containers)[1:]:
            val.delete()
    if selected_form == 'Single Object':
        uploaded_values = single_object_upload_form(uploaded_values, tasks)
        ui.button(
            'Submit',
            on_click=partial(
                _send_single_to_vetting,
                uploaded_values,
                tasks
            )
        ).props('type="submit"')
            
    elif selected_form == 'Multiple Objects':
        uploaded_values = multi_object_upload_form(uploaded_values, tasks)
        ui.button(
            'Submit',
            on_click=partial(
                _multi_send_to_vetting,
                uploaded_values,
                tasks
            )
        ).props('type="submit"')
        
@ui.page(os.path.join(WEB_BASE_URL, "upload"))
async def upload():
                
    tasks = BackgroundTaskStack()
        
    with frame():

        ui.label("Upload Data to OTTER").classes("col-span-5 text-h4")

        # Display the initial
        with ui.grid(rows="auto auto").classes("w-full") as grid:
            selected_tab = ui.toggle(
                ['Single Object', 'Multiple Objects'],
                value='Single Object',
                on_change=lambda e: show_form(
                    e.value,
                    tasks,
                    containers=grid
                )
            ).style("width: 26.25%")
            
            show_form(selected_tab.value, tasks)
            
@ui.page(os.path.join(WEB_BASE_URL, "upload/{dataset_id}/success"))
async def upload_success(dataset_id):

    meta_str, phot_str = io.StringIO(), io.StringIO()
    if "data" in app.storage.user:
        user_data = app.storage.user["data"]
        
        meta_df = pd.DataFrame.from_dict(user_data["meta_df"])
        meta_df.to_markdown(meta_str, index=False, tablefmt="grid")
        
        phot_df = None
        if "phot_df" in user_data:
            phot_df = pd.DataFrame.from_dict(user_data["phot_df"])
            
        if phot_df is not None:
            phot_df.to_markdown(phot_str, index=False, tablefmt="grid")
        
    with frame():
        ui.label("Upload Successful!").classes("text-h4")
        ui.label(
            f"""Your Upload Identifier is {dataset_id}"""
        ).classes("text-h6")
        ui.label(
            "Please save this and use it in any communications with the OTTER team."
        ).classes("text-h6")
        
        msg = f"""
Your dataset has passed our automated vetting process and has now been sent to
our team of vetters. If we have any questions we will reach out to you at the
email you provided.

You should see your data on the OTTER website within ~2 weeks. If you don't
please reach out to the managers!

Thank you for providing your dataset! A summary is shown below, if anything
is incorrect please reach out to the OTTER managers.

**Uploader Information**

**Metadata**

{meta_str.getvalue()}

**Photometry**

{phot_str.getvalue()}

"""
        
        ui.restructured_text(msg)
        
