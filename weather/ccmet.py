import datetime
import logging
import requests
from typing import Dict


class CCMET(object):
    """ Class for getting weather data from the yr.no API
    """

    def __init__(self, lat: float, lon: float, time: datetime.datetime) -> None:
        """ Initialize the class

        :param lat: Latitude of the location
        :param lon: Longitude of the location
        :param time: Time to get the forecast for
        """
        self.lat = lat
        self.lon = lon
        self.time = time
        r = get_forecast_at_time(self.lat, self.lon, self.time)

        self.air_pressure_at_sea_level = r["air_pressure_at_sea_level"]
        self.air_temperature = r["air_temperature"]
        self.cloud_area_fraction = r["cloud_area_fraction"]
        self.relative_humidity = r["relative_humidity"]
        self.wind_from_direction = r["wind_from_direction"]
        self.wind_speed = r["wind_speed"]

    def get_cloud_cover(self) -> float:
        return self.cloud_area_fraction


def get_forecast_at_time(lat: float, lon: float, time: datetime.datetime) -> Dict[str, float]:
    """ Get the forecast at a specific time

    :param lat: Latitude of the location
    :param lon: Longitude of the location
    :param time: Time to get the forecast for
    :return: Forecast data as a dict for the closest available time
    """
    data = get_forecast(lat, lon)
    time_diff = abs(datetime.datetime(1970, 1, 1, 0, 0, 0, 0) - time)
    best_time = None
    for obj in data["properties"]["timeseries"]:
        obj_time = datetime.datetime.fromisoformat(obj["time"][:-1])
        if abs(time - obj_time) < time_diff:
            time_diff = abs(time - obj_time)
            best_time = obj

    r = best_time["data"]["instant"]["details"]
    r["time"] = best_time["time"]
    return r


def get_forecast(lat: float, lon: float) -> Dict[str, float]:
    """ Get the forecast for a specific location

    :param lat: Latitude of the location
    :param lon: Longitude of the location
    :return: Forecast data as a dict
    """
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}

    try:
        r = requests.get(url.strip(), headers=headers, timeout=10)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error getting forecast: {e}")
        raise

    return r.json()


if __name__ == '__main__':
    # Test the class
    logging.basicConfig(level=logging.DEBUG)
    lat = 50.0
    lon = -100.0
    time = datetime.datetime.utcnow()

    ccmet = CCMET(lat, lon, time)
    logging.info(f"Cloud cover: {ccmet.get_cloud_cover()}")
