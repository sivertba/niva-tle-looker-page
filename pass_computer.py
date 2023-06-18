from datetime import datetime
from pyorbital.orbital import Orbital
import requests

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
    satellites = collect_TLEs(satellites)
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



            satellites[satellite][3][loc] = loc_info

    return satellites

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
        default=24*3,
    )

    args = parser.parse_args()

    if args.debug:
        DEBUG = True
        print("Debug mode activated")

    satellites_passes = compute_passes(satellites, locations, args.look_ahead_time)

    for satellite in satellites_passes:
        print(f"Next passes for {satellite}:")
        for loc in satellites_passes[satellite][3]:
            print(f"    {loc}:")
            for pass_list in satellites_passes[satellite][3][loc]:
                print(f"        {pass_list}")
    
