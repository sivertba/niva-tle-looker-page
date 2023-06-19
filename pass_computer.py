from datetime import datetime
from pyorbital.orbital import Orbital
import requests
from weather.ccmet import CCMET
import json
import os
import pandas as pd

# Debug flag
DEBUG = False

# Satellites as dict
satellites = {
    "Landsat-7": [25682, "Line1", "Line2"],
    "Landsat-8": [39084, "Line1", "Line2"],
    "Sentinel-3A": [41335, "Line1", "Line2"],
    "Sentinel-3B": [43437, "Line1", "Line2"],
    "SENTINEL-2A": [40697, "Line1", "Line2"],
    "SENTINEL-2B": [42063, "Line1", "Line2"],
    "HYPSO-1": [51053, "Line1", "Line2"],
}

locations = {
    "Mjøsa": [60.8, 10.8, 0.0],
}


def collect_TLEs(satellites: dict) -> dict:
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
                tol=1
            )

            # extract max elevation datetime and compute elevation
            pass_info = []
            for i in range(len(loc_info)):
                pass_info.append(dict())
                
                pass_info[i]["UTC0_datetime"] = loc_info[i][2].strftime("%Y-%m-%d %H:%M:%SZ")

                temp_obj = sat_obj.get_observer_look(loc_info[i][2], 
                                                         locations[loc][0], 
                                                         locations[loc][1], 
                                                         locations[loc][2])
                
                # reduce to two decimals
                temp_obj = [round(temp_obj[0], 2), round(temp_obj[1], 2)]

                pass_info[i]["azimuth"] = temp_obj[0]
                pass_info[i]["elevation"] = temp_obj[1]

                CCMET_obj = CCMET(locations[loc][0], locations[loc][1], loc_info[i][2])

                if DEBUG:
                    pass_info[i]["cloud_cover"] = 0.0
                else:
                    pass_info[i]["cloud_cover"] = CCMET_obj.get_cloud_cover()

            satellites[satellite][3][loc] = pass_info

    return satellites

def date_table_generator(satellites_passes: dict, 
                         min_elev: float = 50.0, 
                         max_clouds: float = 100.0) -> dict:
    
    date_table = dict()
    for satellite in satellites_passes:
        for loc in satellites_passes[satellite][3]:
            for pass_list in satellites_passes[satellite][3][loc]:
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
    return_str = ""

    for date in date_table:
        df_obj = pd.DataFrame(date_table[date])
        df_obj = df_obj.sort_values(by=["UTC0_datetime"])
        return_str += f"## {date}\n"
        return_str += "Satellite | Location | UTC0 | Azimuth | Elevation | Cloud Cover\n"
        return_str += "--- | --- | --- | --- | --- | ---\n"
        for i in range(len(df_obj)):
            clock_time = df_obj.iloc[i]["UTC0_datetime"].split(" ")[1]
            return_str += f"{df_obj.iloc[i]['satellite']} | {df_obj.iloc[i]['location']} | {clock_time} | {df_obj.iloc[i]['azimuth']} | {df_obj.iloc[i]['elevation']} | {df_obj.iloc[i]['cloud_cover']}\n"
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
        "--look_ahead_time",
        help="How many hours to look ahead",
        type=int,
        default=24*7,
    )

    args = parser.parse_args()

    if args.debug:
        DEBUG = True
        print("Debug mode activated")

    if not DEBUG:
        satellites = collect_TLEs(satellites) # Update TLEs
    elif DEBUG and os.path.isfile("tle/satellites.json"):
        with open("tle/satellites.json", "r") as f:
            satellites = json.load(f)
    else:
        satellites = collect_TLEs(satellites)
        with open("tle/satellites.json", "w") as f:
            json.dump(satellites, f, indent=1)


    satellites_passes = compute_passes(satellites, locations, args.look_ahead_time)

    date_table = date_table_generator(satellites_passes)

    markdown_str = "# Satellite Forecast\n\n"
    markdown_str += date_table_to_markdown(date_table)

    with open("README.md", "w") as f:
        f.write(markdown_str)
    
