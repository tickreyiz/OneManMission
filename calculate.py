import aiohttp
import asyncio
from datetime import datetime, timedelta
import time

async def fetch_temp(session, long, lat, date_str):
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "T2M",
        "community": "AG",
        "longitude": long,
        "latitude": lat,
        "start": date_str,
        "end": date_str,
        "format": "JSON"
    }
    try:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            daily_data = data["properties"]["parameter"]["T2M"]
            return list(daily_data.values())[0]

    except Exception as e:
        print(f"Failed to fetch temperature for {date_str}: {e}")
        return None
    

async def fetch_rain(session, long, lat, date_str):
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "PRECTOTCORR",
        "community": "AG",
        "longitude": long,
        "latitude": lat,
        "start": date_str,
        "end": date_str,
        "format": "JSON"
    }
    try:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            daily_data = data["properties"]["parameter"]["PRECTOTCORR"]
            return list(daily_data.values())[0]

    except Exception as e:
        print(f"Failed to fetch rainfall for {date_str}: {e}")
        return None

async def getExpectedTempAndRainAsync(long, lat, target_date):
    target = datetime.strptime(target_date, "%Y%m%d")
    all_data = {}

    async with aiohttp.ClientSession() as session:
        for j in range(-5, 6):  # ±4 days around the target
            temp_tasks = []
            rain_tasks = []

            for i in range(1, 11):  # past 10 years
                try:
                    year_adjusted = target.replace(year=target.year - i)
                except ValueError:
                    year_adjusted = target.replace(year=target.year - i, day=28)

                new_date = year_adjusted - timedelta(days=j)
                date_str = new_date.strftime("%Y%m%d")

                temp_tasks.append(fetch_temp(session, long, lat, date_str))
                rain_tasks.append(fetch_rain(session, long, lat, date_str))

            temps = await asyncio.gather(*temp_tasks)
            temps = [t for t in temps if t is not None]

            rains = await asyncio.gather(*rain_tasks)
            rains = [r for r in rains if r is not None]

            all_data[j] = {
                "temps": temps,
                "rains": rains
            }

    # Flatten all temps and rains
    # Flatten all temps and rains
    all_temps = [temp for day_data in all_data.values() for temp in day_data["temps"]]
    all_rains = [rain for day_data in all_data.values() for rain in day_data["rains"] if rain is not None]

    # Compute expected temperature
    expected_temp = sum(all_temps) / len(all_temps) if all_temps else None

    # Compute rain probability with threshold 1mm
    rain_events = [r for r in all_rains if r >= 1]  # only count days with rain >= 1mm
    rain_probability = len(rain_events) / len(all_rains) if all_rains else None

    return {
        "expected_temperature": expected_temp,
        "rain_probability": rain_probability
    }


# Example usage
