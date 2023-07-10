from datetime import datetime
from pyorbital.orbital import Orbital
import requests
from weather.ccmet import CCMET
import json
import os
import pypandoc
import numpy as np

# Debug flag
DEBUG = False
VERBOSE = False

file_dir = os.path.dirname(os.path.realpath(__file__))

# set dir of file to current working directory
os.chdir(file_dir)

# Satellites as dict
satellites = {
    "HYPSO-1": {"catnr": 51053, "line1": "Line1", "line2": "Line2", "min_elev": 60},
    "Sentinel-3A": {"catnr": 41335, "line1": "Line1", "line2": "Line2", "min_elev": 90 - 30},
    "Sentinel-3B": {"catnr": 43437, "line1": "Line1", "line2": "Line2", "min_elev": 90 - 30},
    "SENTINEL-2A": {"catnr": 40697, "line1": "Line1", "line2": "Line2", "min_elev": 90 - 25},
    "SENTINEL-2B": {"catnr": 42063, "line1": "Line1", "line2": "Line2", "min_elev": 90 - 25},
}

# Locations as dict
locations = {
    "Mjøsa": {"lat": 60.70, "lon": 10.98, "alt": 0.0},
    "Tyrifjorden": {"lat": 60.03, "lon": 10.18, "alt": 0.0},
    "Hemnessjøen": {"lat": 59.68, "lon": 11.46, "alt": 0.0},
    "Vansjø": {"lat": 59.40, "lon": 10.82, "alt": 0.0},
    "Gjersjøen": {"lat": 59.79, "lon": 10.78, "alt": 0.0},
    "Solbergstrand": {"lat": 59.620, "lon": 10.650, "alt": 0.0},
    "Eikeren": {"lat": 59.6591812, "lon": 9.9289544, "alt": 0.0},
    "Bergsvannet": {"lat": 59.5757441, "lon": 10.0689287, "alt": 0.0},
    "Akersvannet": {"lat": 59.24417, "lon": 10.32762, "alt": 0.0},
    "Skulerudsjøen": {"lat": 59.66426, "lon": 11.54688, "alt": 0.0},
    "Rødenessjøen": {"lat": 59.56363, "lon": 11.60278, "alt": 0.0},
    "Aremarksjøen": {"lat": 59.2606265, "lon": 11.6740797, "alt": 0.0},
    "Femsjøen": {"lat": 59.15268, "lon": 11.49769, "alt": 0.0},
    "Øyeren": {"lat": 59.69713, "lon": 11.23023, "alt": 0.0},
    "Årungen": {"lat": 59.683, "lon": 10.733, "alt": 0.0},
    "Tunevatnet": {"lat": 59.305, "lon": 11.093, "alt": 0.0},
    "Østensjøvannet": {"lat": 59.689, "lon": 10.829, "alt": 0.0},
    "Øymarksjøen": {"lat": 59.38921, "lon": 11.65738, "alt": 0.0},
    "Lundebyvatnet": {"lat": 59.550, "lon": 11.480, "alt": 0.0},
    "Solbergstrand": {"lat": 59.620, "lon": 10.650, "alt": 0.0},
    "Glomma-Løperen": {"lat": 59.170, "lon": 10.960, "alt": 0.0},
}


def collect_TLEs(satellites: dict) -> dict:
    """
    Collects TLEs from celestrak.org and updates the TLEs in the satellites dict

    Args:
        satellites (dict): dict of satellites with TLEs to be updated

    Returns:
        dict: dict of satellites with updated TLEs
    """
    try:
        for satellite in satellites:
            if DEBUG or VERBOSE:
                print(f"collecting TLE for {satellite}")
            url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={satellites[satellite]['catnr']}&FORMAT=TLE"
            tle = requests.get(url)
            tle = tle.text.splitlines()
            satellites[satellite]['line1'] = tle[1]
            satellites[satellite]['line2'] = tle[2]
    except BaseException:
        print('Error. TLE Update not successful')
    return satellites


def compute_passes(
        satellites: dict,
        locations: dict,
        look_ahead_time: int = 24 * 3,
        minimumElevation: float = 40) -> dict:
    """
    Computes passes for each satellite at each location

    Args:
        satellites (dict): dict of satellites with TLEs
        locations (dict): dict of locations
        look_ahead_time (int, optional): look ahead time in hours. Defaults to 24*3.
        minimumElevation (float, optional): minimum elevation in degrees. Defaults to 40.

    Returns:
        dict: dict of satellites with passes for each location
    """
    if DEBUG:
        print("collect_TLEs() successful")
    for satellite in satellites:
        # Get orbital object from pyorbital using the TLEs
        sat_obj = Orbital(
            satellite,
            line1=satellites[satellite]['line1'],
            line2=satellites[satellite]['line2']
        )

        satellites[satellite]['passes'] = dict()
        # Get next passes for each location
        for loc in locations:
            loc_info = sat_obj.get_next_passes(
                datetime.utcnow(),
                look_ahead_time,
                locations[loc]['lon'],
                locations[loc]['lat'],
                locations[loc]['alt'],
                tol=0.001,
                horizon=int(minimumElevation // 1)
            )

            # extract max elevation datetime and compute elevation
            pass_info = get_pass_info_list(locations, sat_obj, loc, loc_info)
            satellites[satellite]['passes'][loc] = pass_info

    return satellites


def get_pass_info_list(
        locations: dict,
        sat_obj: Orbital,
        loc: str,
        loc_info: list
) -> list:
    """
    Extracts max elevation datetime and computes elevation for each pass

    Args:
        locations (dict): dict of locations
        sat_obj (Orbital): pyorbital orbital object
        loc (str): location
        loc_info (list): list of passes

    Returns:
        list: list of passes with max elevation datetime and elevation
    """
    import time
    from pyorbital.orbital import astronomy

    pass_info = []
    for i in range(len(loc_info)):
        pass_info.append(dict())

        pass_info[i]["UTC0_datetime"] = loc_info[i][2].strftime(
            "%Y-%m-%d %H:%M:%SZ")

        temp_obj = sat_obj.get_observer_look(loc_info[i][2],
                                             locations[loc]["lon"],
                                             locations[loc]["lat"],
                                             locations[loc]["alt"])

        # reduce to two decimals
        temp_obj = [round(temp_obj[0], 2), round(temp_obj[1], 2)]

        pass_info[i]["azimuth"] = temp_obj[0]
        pass_info[i]["elevation"] = temp_obj[1]

        # check sun zenith angle
        pass_info[i]["sun_zenith_angle"] = astronomy.sun_zenith_angle(
            loc_info[i][2], locations[loc]["lon"], locations[loc]["lat"])

        if DEBUG:
            pass_info[i]["cloud_cover"] = -1
        elif pass_info[i]["sun_zenith_angle"] > 70:
            pass_info[i]["cloud_cover"] = 101
        else:
            # Make a grid of .05 degree around the location and compute cloud
            # cover for each point.
            median_cloud_cover = []
            for lat_steps in range(-1, 2):
                for lon_steps in range(-1, 2):
                    CCMET_obj = CCMET(
                        locations[loc]["lat"] + lat_steps * 0.05,
                        locations[loc]["lon"] + lon_steps * 0.05,
                        loc_info[i][2])
                    median_cloud_cover.append(CCMET_obj.get_cloud_cover())
            # compute median cloud cover
            pass_info[i]["cloud_cover"] = np.median(median_cloud_cover)
            if VERBOSE:
                print(
                    f"cloud cover for {loc} at {pass_info[i]['UTC0_datetime']} is {pass_info[i]['cloud_cover']}")
    return pass_info


def date_table_generator(satellites_passes: dict,
                         min_elev: float = 40.0,
                         max_clouds: float = 100.0) -> dict:
    """
    Generates a date table from the passes

    Args:
        satellites_passes (dict): dict of satellites with passes for each location
        min_elev (float, optional): minimum elevation in degrees. Defaults to 40.0.
        max_clouds (float, optional): maximum cloud cover in percent. Defaults to 100.0.

    Returns:
        dict: dict of dates with passes
    """
    from pyorbital.orbital import astronomy

    min_elev_static = min_elev

    date_table = dict()
    for satellite in satellites_passes:
        for loc in satellites_passes[satellite]["passes"]:
            for pass_list in satellites_passes[satellite]["passes"][loc]:
                # check sun zenith angle
                sza = astronomy.sun_zenith_angle(pass_list["UTC0_datetime"],
                                                 locations[loc]["lon"],
                                                 locations[loc]["lat"])
                if sza > 55.0:
                    continue

                # check if min_elev key exists in satellite dict
                if "min_elev" in satellites_passes[satellite]:
                    min_elev = satellites_passes[satellite]["min_elev"]
                else:
                    min_elev = min_elev_static

                if pass_list["elevation"] >= min_elev and pass_list["cloud_cover"] <= max_clouds:
                    # get the date as a string
                    date = pass_list["UTC0_datetime"].split(" ")[0]
                    if date not in date_table:
                        date_table[date] = []
                    dict_obj = pass_list
                    dict_obj["satellite"] = satellite
                    dict_obj["location"] = loc
                    date_table[date].append(dict_obj)

    return date_table


def date_table_to_markdown(date_table: dict, locations: dict) -> str:
    """ Generates a markdown table from the date table

    Args:
        date_table (dict): dict of dates with passes
        locations (dict): dict of locations with lat, lon and alt

    Returns:
        str: markdown table
    """
    return_str = ""

    entries = []
    for date in date_table.keys():
        passes = date_table[date]
        passes.sort(key=lambda x: x["UTC0_datetime"])
        entry = ""
        for i in range(len(passes)):
            pass_info = passes[i]
            clock_time = pass_info["UTC0_datetime"].split(" ")[1]
            lat_temp = locations[pass_info["location"]]["lat"]
            lon_temp = locations[pass_info["location"]]["lon"]
            loc_lat_lon = pass_info["location"] + f" ({lat_temp}, {lon_temp})"
            entry += f"{pass_info['satellite']} | {loc_lat_lon} | {clock_time} | {pass_info['elevation']} | {pass_info['cloud_cover']}\n"

        entries.append([date, entry])

    # concatenate all entries in the correct order
    sorted_entries = sorted(entries, key=lambda x: x[0])
    return_str = ""
    for entry in sorted_entries:
        return_str += f"## {entry[0]}\n"
        return_str += "Satellite | Location | UTC+0 | Elevation | Cloud Cover\n"
        return_str += "--- | --- | --- | --- | --- | ---\n"
        return_str += entry[1]
    return_str += "\n\n"
    return return_str


def _get_cli_args():
    import argparse
    parser = argparse.ArgumentParser()

    print("Running pass_computer.py")

    parser.add_argument(
        "--debug",
        help="Print debug information",
        action="store_true",
    )

    parser.add_argument(
        "--look_ahead_hrs",
        help="How many hours to look ahead",
        type=int,
        default=24 * 6,
    )

    parser.add_argument(
        "--minelev",
        help="Minimum elevation for passes",
        type=float,
        default=40.0,
    )

    parser.add_argument(
        "--maxclouds",
        help="Maximum cloud cover for passes",
        type=float,
        default=101.0,
    )

    parser.add_argument("--gitupload",
                        help="Upload to github",
                        action="store_true")

    parser.add_argument(
        "--verbose",
        help="Print verbose information",
        action="store_true",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = _get_cli_args()

    # save start time of script
    start_time = datetime.utcnow()

    if args.debug:
        DEBUG = True
        print("Debug mode activated")

    if args.verbose:
        VERBOSE = True
        print("Verbose mode activated")

    if not DEBUG:
        satellites = collect_TLEs(satellites)  # Update TLEs
    elif DEBUG and os.path.isfile("tle/satellites.json"):
        with open("tle/satellites.json", "r") as f:
            satellites = json.load(f)
    else:
        satellites = collect_TLEs(satellites)
        with open("tle/satellites.json", "w") as f:
            json.dump(satellites, f, indent=1)

    satellites_passes = compute_passes(
        satellites, locations, args.look_ahead_hrs, args.minelev)

    date_table = date_table_generator(
        satellites_passes, args.minelev, args.maxclouds)

    markdown_str = "# Satellite Forecaster\n\n"

    # write some info about what the script does to the markdown file
    markdown_str += "This website contains a forecast of satellite passes for the next week. " + \
        "At the bottom of the site you can see the different satellites and the different locations" + \
        " that are used in the forecast. The forecast is generated using the pyorbital library. " + \
        "The forecast is generated for the next week and is updated every day. " + \
        "The cloud cover is retrieved from the Norwegian Meteorological Institute. " + \
        "The cloud cover is given as the median of a grid at the location."
    markdown_str += "The forecast is generated using the following parameters:\n\n"
    markdown_str += f"Maximum cloud cover: {args.maxclouds} percent\n\n"
    markdown_str += f"Look ahead time: {args.look_ahead_hrs} hours\n\n"
    markdown_str += f" \n\n"
    script_time = datetime.utcnow() - start_time
    # with two decimals in seconds
    script_time = round(script_time.total_seconds(), 2)
    markdown_str += f"Time to complete script (seconds): {script_time}\n\n"

    markdown_str += date_table_to_markdown(date_table, locations)

    # add table of locations
    markdown_str += "## Locations\n\n"
    markdown_str += "Location | Latitude | Longitude | Altitude\n"
    markdown_str += "--- | --- | --- | ---\n"
    for loc in locations:
        l0 = locations[loc]["lat"]
        l1 = locations[loc]["lon"]
        l2 = locations[loc]["alt"]
        markdown_str += f"{loc} | {l0} | {l1} | {l2}\n"

    # add table of satellites
    markdown_str += "\n\n## Satellites\n\n"
    markdown_str += "Satellite | NORAD ID | Minimum Elevation\n"
    markdown_str += "--- | --- | ---\n"
    for sat in satellites:
        sat_name = sat
        norad_id = satellites[sat]["catnr"]
        min_elev = satellites[sat]["min_elev"]
        markdown_str += f"{sat_name} | {norad_id} | {min_elev}\n"

    # convert markdown to html
    output = "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n</head>\n<body>\n"
    output += '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css">\n'
    output += "<div style=\"width: 800px; margin-left: auto; margin-right: auto;\">\n"
    pdoc_args = ['--mathjax']
    output += pypandoc.convert_text(markdown_str,
                                    'html5',
                                    format='md',
                                    extra_args=pdoc_args,
                                    encoding='utf-8')
    output += "</div>"
    output += "\n</body>\n</html>"

    output = output.replace(
        "<table>",
        "<table class='table' width=\"750px\" style=\"margin-left: auto; margin-right: auto;\">")
    # make all table elements center
    output = output.replace("<td>", "<td align=\"center\">")
    output = output.replace("<th>", "<th align=\"center\">")
    output = output.replace("<h1", "<h1 class=\"title\" ")
    output = output.replace("<h2", "<h2 class=\"subtitle\" ")

    with open("index.html", "w") as f:
        f.write(output)

    if args.gitupload:
        print("Uploading to github")
        os.system("git add *.html *.py")
        # get date of today
        today = datetime.utcnow().strftime("%Y-%m-%d")
        os.system(f"git commit -m \"Update index.html, Day of push {today}\"")
	#os.system("git pull")
        os.system("git push --force")
