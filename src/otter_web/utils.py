from nicegui import ui


def _parse_table_info(event_data, keys):
    src_ref = {
        ed_srcs["alias"]: {**ed_srcs, "idx": i}
        for i, ed_srcs in enumerate(event_data["sources"])
    }

    cols = [
        {
            "name": "name",
            "required": True,
            "field": "name",
            "label": "",
            "align": "right",
            "sortable": True,
            "classes": "bg-blue-1 text-bold",
        },
        *[
            {
                "name": f"col-{src['idx']}",
                "required": True,
                "field": f"col-{src['idx']}",
                "label": f"{src['name']}",
                "align": "right",
                "sortable": True,
            }
            for src in src_ref.values()
        ],
    ]

    rows = []

    for key, values in event_data.items():
        if key not in keys or type(values) is not list:
            continue

        rows.append(
            {
                "name": f"{key}{' (' + values[0]['u_value'] + ')' if values[0]['u_value'] is not None else ''}",
                **{
                    f"col-{src_ref[alias]['idx']}": val["value"]
                    for val in values
                    for alias in val["source"]
                },
            }
        )

    return cols, rows


def _parse_event_data(event_data):
    uv_phot_data, xray_phot_data, radio_phot_data = {}, {}, {}

    for entry in event_data["photometry"]:
        time = entry["time"][0]
        tele = entry.get("telescope")
        inst = entry.get("instrument")

        # UV/optical
        band = entry.get("band")
        mag = entry.get("magnitude", 0.0)
        e_mag = entry.get("e_magnitude", 0.0)

        # Radio
        freq = entry.get("frequency")
        flux_dens = entry.get("fluxdensity")
        e_flux_dens = entry.get("e_fluxdensity")

        # X-ray
        energy = entry.get("energy")
        flux = entry.get("flux")
        e_flux = entry.get("e_flux")

        if mag is not None:
            uv_phot_data.setdefault("tele", []).append(tele)
            uv_phot_data.setdefault("inst", []).append(inst)
            uv_phot_data.setdefault("band", []).append(band)
            uv_phot_data.setdefault("x", []).append(time)
            uv_phot_data.setdefault("y", []).append(mag)
            uv_phot_data.setdefault("y_err", []).append(e_mag)

        if flux is not None:
            xray_phot_data.setdefault("tele", []).append(tele)
            xray_phot_data.setdefault("inst", []).append(inst)
            xray_phot_data.setdefault("energy", []).append(str(energy))
            xray_phot_data.setdefault("x", []).append(time)
            xray_phot_data.setdefault("y", []).append(flux)
            xray_phot_data.setdefault("y_err", []).append(e_flux)

        if flux_dens is not None:
            radio_phot_data.setdefault("tele", []).append(tele)
            radio_phot_data.setdefault("inst", []).append(inst)
            radio_phot_data.setdefault("freq", []).append(freq)
            radio_phot_data.setdefault("x", []).append(time)
            radio_phot_data.setdefault("y", []).append(flux_dens)
            radio_phot_data.setdefault("y_err", []).append(e_flux_dens)

    return uv_phot_data, xray_phot_data, radio_phot_data


def _parse_cat_table(all_events):
    cols = [
        {
            "name": "link",
            "label": "",
            "field": "link",
            "sortable": True,
            "headerStyle": "width: 10px",
        },
        {
            "name": "name",
            "label": "Name",
            "field": "name",
            "required": True,
            "align": "left",
        },
        {
            "name": "redshift",
            "label": "Redshift",
            "field": "redshift",
            "sortable": True,
        },
        {
            "name": "ra",
            "label": "R.A.",
            "field": "ra",
            "sortable": True,
        },
        {"name": "dec", "label": "Dec", "field": "dec", "sortable": True},
    ]

    rows = [
        {
            "name": x["name"],
            "redshift": x["redshift"][0]["value"]
            if x.get("redshift") is not None
            else "--",
            "ra": x["ra"][0]["value"],
            "dec": x["dec"][0]["value"],
            "link": f"/event/view/{x['_id']}",
        }
        for x in all_events
    ]

    return cols, rows
