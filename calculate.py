import aiohttp
import asyncio
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression

# ----------------------------
# NASA API Fetch Functions (unchanged)
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
            if response.status == 429:
                raise RuntimeError("Rate limit exceeded (HTTP 429) from NASA POWER API")
            response.raise_for_status()
            data = await response.json()
            daily_data = data["properties"]["parameter"]["T2M"]
            return list(daily_data.values())[0]
    except Exception as e:
        if "rate limit" in str(e).lower() or "429" in str(e):
            raise
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
            if response.status == 429:
                raise RuntimeError("Rate limit exceeded (HTTP 429) from NASA POWER API")
            response.raise_for_status()
            data = await response.json()
            daily_data = data["properties"]["parameter"]["PRECTOTCORR"]
            return list(daily_data.values())[0]
    except Exception as e:
        if "rate limit" in str(e).lower() or "429" in str(e):
            raise
        return None


# ----------------------------
# Upgraded Prediction Function
# ----------------------------
async def get_expected_temp_and_rain(long, lat, target_date, return_history=False):
    target = datetime.strptime(target_date, "%Y%m%d")
    temps = []
    rains = []
    history = []

    async with aiohttp.ClientSession() as session:
        for j in range(-4, 5):  # ±4 day window
            await asyncio.sleep(0.2)
            temp_tasks = []
            rain_tasks = []

            for i in range(1, 11):  # past 10 years
                try:
                    year_adjusted = target.replace(year=target.year - i)
                except ValueError:
                    year_adjusted = target.replace(year=target.year - i, day=28)

                new_date = year_adjusted + timedelta(days=j)
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
                    # Features: [year, day_offset, month, day_of_year]
                    month = new_date.month
                    day_of_year = new_date.timetuple().tm_yday
                    temps.append(([year_actual, j, month, day_of_year], t))
                    if return_history:
                        history.append({"year": year_actual, "offset": j, "temp": t})
                if r is not None and return_history:
                    history.append({"year": year_actual, "offset": j, "rain": r})

    # ----------------------------
    # Temperature Regression
    # ----------------------------
    if len(temps) >= 2:
        X_temp = [feat for feat, _ in temps]
        y_temp = [val for _, val in temps]
        temp_model = LinearRegression()
        temp_model.fit(X_temp, y_temp)

        # Predict for target day (offset=0)
        target_features = [[target.year, 0, target.month, target.timetuple().tm_yday]]
        predicted_temp = temp_model.predict(target_features)[0]
        predicted_temp = max(min(predicted_temp, 50), -50)
    else:
        predicted_temp = None

    # ----------------------------
    # Rain Logistic Regression
    # ----------------------------
# ----------------------------
# Rain Prediction (Robust Version)
# ----------------------------
# ----------------------------
# Robust Rain Probability (Historical Frequency)
# ----------------------------
    rain_values = [
        entry['rain'] for entry in history
        if 'rain' in entry and entry['rain'] is not None
    ]

    if rain_values:
        # Count days with rain >= 1 mm
        rainy_days = sum(1 for r in rain_values if r >= 1)
        predicted_rain_prob = rainy_days / len(rain_values)
    else:
        predicted_rain_prob = None

    # Optional: clamp probability to [0,1] (safety)
    if predicted_rain_prob is not None:
        predicted_rain_prob = min(max(predicted_rain_prob, 0.0), 1.0)

        # Return output same as before
        return (
            (predicted_temp, predicted_rain_prob, history)
            if return_history
            else (predicted_temp, predicted_rain_prob)
        )

