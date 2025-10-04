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
async def get_expected_temp_and_rain(long, lat, target_date):
    target = datetime.strptime(target_date, "%Y%m%d")
    day_offsets = []
    temps = []
    rains = []

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
                date_str = new_date.strftime("%Y%m%d")

                temp_tasks.append(fetch_temp(session, long, lat, date_str))
                rain_tasks.append(fetch_rain(session, long, lat, date_str))

            year_temps = await asyncio.gather(*temp_tasks)
            year_rains = await asyncio.gather(*rain_tasks)

            for t, r in zip(year_temps, year_rains):
                if t is not None:
                    day_offsets.append([j])
                    temps.append(t)
                if r is not None:
                    rains.append((j, r))

    # -----------------------
    # Linear Regression for temperature
    # -----------------------
    predicted_temp = None
    if temps:
        temp_model = LinearRegression()
        temp_model.fit(day_offsets, temps)
        predicted_temp = temp_model.predict([[0]])[0]

    # -----------------------
    # Rain probability
    # -----------------------
    if rains:
        # Use historical average for rain probability
        predicted_rain_prob = np.mean([1 if r[1] >= 1 else 0 for r in rains])
    else:
        predicted_rain_prob = 0  # fallback to 0%

    return predicted_temp, predicted_rain_prob


#latitude = 41.0462    # San Francisco
#longitude = 29.1357

# Target date in YYYYMMDD format
#target_date = "20251009"

# Call the async function
#predicted_temp, predicted_rain_prob = asyncio.run(
#    get_expected_temp_and_rain(longitude, latitude, target_date)
#)

#print(f"Predicted Temperature: {predicted_temp:.2f} °C")
#print(f"Predicted Rain Probability: {predicted_rain_prob*100:.1f}%")