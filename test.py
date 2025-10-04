import aiohttp
import asyncio
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import numpy as np

# ----------------------------
# NASA API Fetch Functions
# ----------------------------
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

# ----------------------------
# Prediction with Linear Regression
# ----------------------------
async def get_expected_temp_and_rain(long, lat, target_date, return_history=False):
    target = datetime.strptime(target_date, "%Y%m%d")
    temps = []
    rains = []
    history = []

    async with aiohttp.ClientSession() as session:
        for j in range(-4, 5):  # ±4 days
            temp_tasks = []
            rain_tasks = []

            for i in range(1, 11):  # past 10 years
                try:
                    year_adjusted = target.replace(year=target.year - i)
                except ValueError:
                    year_adjusted = target.replace(year=target.year - i, day=28)

                new_date = year_adjusted + timedelta(days=j)
                # Skip if new_date went outside intended year
                if new_date.year != year_adjusted.year:
                    continue

                date_str = new_date.strftime("%Y%m%d")
                temp_tasks.append(fetch_temp(session, long, lat, date_str))
                rain_tasks.append(fetch_rain(session, long, lat, date_str))

            year_temps = await asyncio.gather(*temp_tasks)
            year_rains = await asyncio.gather(*rain_tasks)

            for t, r, i_year in zip(year_temps, year_rains, range(1, len(year_temps)+1)):
                year_actual = target.year - i_year
                if t is not None:
                    temps.append((j, t))
                    if return_history:
                        history.append({"year": year_actual, "offset": j, "temp": t})
                if r is not None and return_history:
                    history.append({"year": year_actual, "offset": j, "rain": r})

    # Prepare regression for temperature
    day_offsets = [[offset] for offset, _ in temps]
    temp_values = [t for _, t in temps]

    if len(temp_values) >= 2:
        from sklearn.linear_model import LinearRegression
        temp_model = LinearRegression()
        temp_model.fit(day_offsets, temp_values)
        predicted_temp = temp_model.predict([[0]])[0]
        predicted_temp = max(min(predicted_temp, 50), -50)  # clamp
    else:
        predicted_temp = None

    # Rain probability
    rain_filtered = [(entry['offset'], entry.get('rain')) for entry in history if 'rain' in entry]
    rain_targets = [1 if r[1] >= 1 else 0 for r in rain_filtered if r[1] is not None]
    rain_offsets = [[r[0]] for r in rain_filtered if r[1] is not None]

    if rain_offsets:
        from sklearn.linear_model import LinearRegression
        rain_model = LinearRegression()
        rain_model.fit(rain_offsets, rain_targets)
        predicted_rain_prob = rain_model.predict([[0]])[0]
        predicted_rain_prob = min(max(predicted_rain_prob, 0), 1)
    else:
        predicted_rain_prob = None

    return (predicted_temp, predicted_rain_prob, history) if return_history else (predicted_temp, predicted_rain_prob)



