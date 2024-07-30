import json
from datetime import datetime
from otter_web.server.models import (
    DateReferenceCreate,
    ClassificationCreate,
    CoordinateCreate,
    NameCreate,
    NameAliasCreate,
    PhotometryCreate,
    DistanceCreate,
    HostCreate,
    TransientCreate,
)
from astropy.time import Time
from astropy.coordinates import SkyCoord

import httpx
from pathlib import Path


def parse_datetime(date_string, date_format, coerce_format=None):
    try:
        fin_time = Time(date_string, format=date_format.lower()).iso
    except ValueError:
        try:
            fin_time = datetime.fromisoformat(date_string)
        except ValueError:
            # Handle non-ISO formats with excessive fractional seconds
            if "." in date_string:
                date_string, frac_seconds = date_string.split(".")
                # Truncate fractional seconds to microseconds (6 digits)
                frac_seconds = frac_seconds[:6]
                date_string = f"{date_string}.{frac_seconds}"
            fin_time = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S.%f")

    return (
        Time(fin_time).iso
        if coerce_format is None
        else str(Time(fin_time).to_value(coerce_format))
    )


def parse_date_reference(data):
    refs = []

    for item in data:
        refs.append(
            DateReferenceCreate(
                value=parse_datetime(
                    str(item["value"]).strip(), item.get("date_format", "mjd")
                ),
                date_format="iso",
                date_type=item["date_type"],
                default=item.get("default", False),
            )
        )

    return refs


def parse_classification(data):
    return [
        ClassificationCreate(
            object_class=item["object_class"],
            confidence=item["confidence"],
            default=item.get("default", False),
        )
        for item in data
    ]


def parse_coordinate(data):
    res = []

    for item in data:
        if item["coordinate_type"].lower() == "galactic":
            pos = SkyCoord(
                item["l"],
                item["b"],
                frame="galactic",
                unit=(item["l_units"], item["b_units"]),
            )
            pos = pos.icrs
            coord_type = "equatorial"
        else:
            pos = SkyCoord(
                item["ra"], item["dec"], unit=(item["ra_units"], item["dec_units"])
            )
            coord_type = item["coordinate_type"]

        res.append(
            CoordinateCreate(
                ra=pos.ra.to_string(),
                dec=pos.dec.to_string(),
                ra_units=pos.ra.unit.to_string(),
                dec_units=pos.dec.unit.to_string(),
                coordinate_type=coord_type,
                default=item.get("default", False),
            )
        )

    return res


def parse_name(data):
    return NameCreate(
        default_name=data["default_name"],
        aliases=[
            NameAliasCreate(value=alias["value"]) for alias in data.get("alias", [])
        ],
    )


def parse_photometry(data):
    res = []

    for item in data:
        dates = item["date"]
        date_formats = item.get("date_format", "mjd")
        upperlim = item.get("upperlimit", [False] * len(item["raw"]))
        corr_host = item.get("corr_host")
        corr_av = item.get("corr_av")

        if not isinstance(dates, list):
            dates = [dates]

        if not isinstance(date_formats, list):
            date_formats = [date_formats]
            date_formats = [date_formats[0]] * len(dates)

        if not isinstance(upperlim, list):
            upperlim = [upperlim]

        if isinstance(corr_host, list):
            corr_host = corr_host[0]

        if isinstance(corr_av, list):
            corr_av = corr_av[0]

        res.append(
            PhotometryCreate(
                raw=item["raw"],
                raw_err=item.get("raw_err", []),
                raw_units=item["raw_units"],
                filter_key=item["filter_key"],
                obs_type=item["obs_type"],
                date=[
                    parse_datetime(dates[i], date_formats[i], coerce_format="mjd")
                    for i in range(len(dates))
                ],
                date_format=date_formats,
                upperlimit=upperlim,
                telescope=item.get("telescope", "None"),
                corr_k=item.get("corr_k"),
                corr_av=corr_av,
                corr_host=corr_host,
                corr_hostav=item.get("corr_hostav"),
            )
        )

    return res


def parse_distance(data):
    res = []

    for item in data:
        if item.get("value") is None:
            print("Distance value is None.")
            continue

        res.append(
            DistanceCreate(
                value=item["value"],
                distance_type=item["distance_type"],
                unit=item.get("unit"),
                default=item.get("default", False),
            )
        )

    return res


def parse_host(data):
    return [
        HostCreate(
            host_name="Unknown" if item["host_name"] is None else item["host_name"],
            host_ra=item["host_ra"],
            host_dec=item["host_dec"],
            host_ra_units=item["host_ra_units"],
            host_dec_units=item["host_dec_units"],
        )
        for item in data
    ]


def parse_transient(path):
    with open(path) as f:
        data = json.load(f)
        data["schema_version_id"] = 1

        print(path.stem)

        transient_data = {
            "date_references": (
                parse_date_reference(data["date_reference"])
                if "date_reference" in data
                else []
            ),
            "classifications": parse_classification(data["classification"]),
            "coordinates": parse_coordinate(data["coordinate"]),
            "name": parse_name(data["name"]),
            "photometries": (
                parse_photometry(data["photometry"]) if "photometry" in data else []
            ),
            "distances": parse_distance(data["distance"]) if "distance" in data else [],
            "hosts": parse_host(data["host"]) if "host" in data else [],
            "schema_version_id": data["schema_version_id"],
        }

        t = TransientCreate(**transient_data)

    return t


for path in Path("/Users/nmearl/projects/otterdb/.otter").rglob("*.json"):
    t = parse_transient(path)
    transient_json = t.model_dump_json()

    # Define the endpoint URL
    url = "http://127.0.0.1:10202/transients/"

    # Submit the data using httpx
    with httpx.Client() as client:
        response = client.post(
            url, data=transient_json, headers={"Content-Type": "application/json"}
        )

    # Check the response
    if response.status_code == 200:
        print("Transient data submitted successfully.")
        # print(response.json())
    else:
        print(f"Failed to submit transient data. Status code: {response.status_code}")
        # print(response.json())
