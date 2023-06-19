from datetime import datetime
from pyorbital.orbital import Orbital
import requests
from weather.ccmet import CCMET
import json
import os
import pandas as pd
import pypandoc

# Debug flag
DEBUG = False

file_dir = os.path.dirname(os.path.realpath(__file__))

# Satellites as dict
satellites = {
    # "Landsat-7": [25682, "Line1", "Line2"],
    # "Landsat-8": [39084, "Line1", "Line2"],
    "HYPSO-1": [51053, "Line1", "Line2"],
    "Sentinel-3A": [41335, "Line1", "Line2"],
    "Sentinel-3B": [43437, "Line1", "Line2"],
    "SENTINEL-2A": [40697, "Line1", "Line2"],
    "SENTINEL-2B": [42063, "Line1", "Line2"],
}

# Locations as dict
locations = {
    "Mjøsa": [60.70, 10.98, 0.0],
    "Tyrifjorden": [60.03, 10.18, 0.0],
    "Hemnessjøen": [59.68, 11.46, 0.0],
    "Vansjø": [59.40, 10.82, 0.0],
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
            if DEBUG:
                print(f"collecting TLE for {satellite}")
            url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={satellites[satellite][0]}&FORMAT=TLE"
            tle = requests.get(url)
            tle = tle.text.splitlines()
            satellites[satellite][1] = tle[1]
            satellites[satellite][2] = tle[2]
    except:
        print('Error. TLE Update not successful')
    return satellites


def compute_passes(satellites: dict, locations: dict, look_ahead_time: int = 24*3) -> dict:
    """
    Computes passes for each satellite at each location

    Args:
        satellites (dict): dict of satellites with TLEs
        locations (dict): dict of locations
        look_ahead_time (int, optional): look ahead time in hours. Defaults to 24*3.

    Returns:
        dict: dict of satellites with passes for each location
    """
    if DEBUG:
        print("collect_TLEs() successful")
    for satellite in satellites:
        # Get orbital object from pyorbital using the TLEs
        sat_obj = Orbital(
            satellite,
            line1=satellites[satellite][1],
            line2=satellites[satellite][2]
        )

        satellites[satellite].append(dict())
        # Get next passes for each location
        for loc in locations:
            loc_info = sat_obj.get_next_passes(
                datetime.utcnow(),
                look_ahead_time,
                locations[loc][0],
                locations[loc][1],
                locations[loc][2],
                tol=0.001,
                horizon=0.0
            )

            # extract max elevation datetime and compute elevation
            pass_info = []
            for i in range(len(loc_info)):
                pass_info.append(dict())

                pass_info[i]["UTC0_datetime"] = loc_info[i][2].strftime(
                    "%Y-%m-%d %H:%M:%SZ")

                temp_obj = sat_obj.get_observer_look(loc_info[i][2],
                                                     locations[loc][0],
                                                     locations[loc][1],
                                                     locations[loc][2])

                # reduce to two decimals
                temp_obj = [round(temp_obj[0], 2), round(temp_obj[1], 2)]

                pass_info[i]["azimuth"] = temp_obj[0]
                pass_info[i]["elevation"] = temp_obj[1]

                if DEBUG:
                    pass_info[i]["cloud_cover"] = -1
                else:
                    CCMET_obj = CCMET(
                        locations[loc][0], locations[loc][1], loc_info[i][2])
                    pass_info[i]["cloud_cover"] = CCMET_obj.get_cloud_cover()

            satellites[satellite][3][loc] = pass_info

    return satellites


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

    date_table = dict()
    for satellite in satellites_passes:
        for loc in satellites_passes[satellite][3]:
            for pass_list in satellites_passes[satellite][3][loc]:
                # check sun zenith angle
                sza = astronomy.sun_zenith_angle(pass_list["UTC0_datetime"],
                                                 locations[loc][0],
                                                 locations[loc][1])
                if sza > 90.0:
                    continue
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


def date_table_to_markdown(date_table: dict) -> str:
    """ Generates a markdown table from the date table

    Args:
        date_table (dict): dict of dates with passes

    Returns:
        str: markdown table
    """
    return_str = ""

    entries = []
    for date in date_table.keys():
        df_obj = pd.DataFrame(date_table[date])
        df_obj = df_obj.sort_values(by=["UTC0_datetime"])
        entry = ""
        for i in range(len(df_obj)):
            clock_time = df_obj.iloc[i]["UTC0_datetime"].split(" ")[1]
            loc_lat_lon = df_obj.iloc[i]["location"] + \
                f" ({locations[df_obj.iloc[i]['location']][0]}, {locations[df_obj.iloc[i]['location']][1]})"
            entry += f"{df_obj.iloc[i]['satellite']} | {loc_lat_lon} | {clock_time} | {df_obj.iloc[i]['elevation']} | {df_obj.iloc[i]['cloud_cover']}\n"

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


if __name__ == "__main__":
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
        default=24*7,
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
        default=50.0,
    )

    args = parser.parse_args()

    if args.debug:
        DEBUG = True
        print("Debug mode activated")

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
        satellites, locations, args.look_ahead_hrs)

    date_table = date_table_generator(satellites_passes, args.minelev, args.maxclouds)

    markdown_str = "# Satellite Forecast\n\n"

    # write some info about what the script does to the markdown file
    markdown_str += "This website contains a forecast of satellite passes for the next week. " + \
        "At the bottom of the site you can see the different satellites and the different locations" + \
        " that are used in the forecast. The forecast is generated using the pyorbital library. " + \
        "The forecast is generated for the next week and is updated every day. " + \
        "\n\n"
    
    markdown_str += "The forecast is generated using the following parameters:\n\n"
    markdown_str += f"Minimum elevation: {args.minelev} degrees\n\n"
    markdown_str += f"Maximum cloud cover: {args.maxclouds} percent\n\n"
    markdown_str += f"Look ahead time: {args.look_ahead_hrs} hours\n\n"

    markdown_str += date_table_to_markdown(date_table)

    # add table of locations
    markdown_str += "## Locations\n\n"
    markdown_str += "Location | Latitude | Longitude | Altitude\n"
    markdown_str += "--- | --- | --- | ---\n"
    for loc in locations:
        markdown_str += f"{loc} | {locations[loc][0]} | {locations[loc][1]} | {locations[loc][2]}\n"

    # add table of satellites
    markdown_str += "\n\n## Satellites\n\n"
    markdown_str += "Satellite | NORAD ID | Line 1 | Line 2\n"
    markdown_str += "--- | --- | --- | ---\n"
    for sat in satellites:
        markdown_str += f"{sat} | {satellites[sat][0]} | {satellites[sat][1]} | {satellites[sat][2]}\n"

    with open("README.md", "w") as f:
        f.write(markdown_str)

    # convert markdown to html
    output = "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n</head>\n<body>\n"
    # make entire website 900 px wide
    output += "<div style=\"width: 900px; margin-left: auto; margin-right: auto;\">\n"
    pdoc_args = ['--mathjax']
    output += pypandoc.convert_text(markdown_str, 'html5', format='md', extra_args=pdoc_args, encoding='utf-8')
    output += "</div>"
    output += "\n</body>\n</html>"

    output = output.replace("<table>", "<table width=\"800px\" style=\"margin-left: auto; margin-right: auto;\">")
    # make all table elements center
    output = output.replace("<td>", "<td align=\"center\">")
    output = output.replace("<th>", "<th align=\"center\">")

    with open("index.html", "w") as f:
        f.write(output)