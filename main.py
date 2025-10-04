import requests
from datetime import datetime, timedelta

def getPast10YearsTemps(long, lat, target_date):
    """
    Fetches temperature (T2M) data for the same date across the last 10 years
    using the NASA POWER API.

    Args:
        long (float): Longitude of the location
        lat (float): Latitude of the location
        target_date (str): Target date in 'YYYYMMDD' format (e.g., '20251004')

    Returns:
        list of floats: Temperatures (°C) for that date in each of the past 10 years
    """

    # Parse the target date
    target = datetime.strptime(target_date, "%Y%m%d")
    all_temps= {}
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    all_temps = {}  # store temps for each day offset

    for j in range(-10, 10):
        temps = []
        for i in range(1, 11):
            try:
                year_adjusted = target.replace(year=target.year - i)
            except ValueError:
                year_adjusted = target.replace(year=target.year - i, day=28)

            new_date = year_adjusted - timedelta(days=j)
            start_end = new_date.strftime("%Y%m%d")

            params = {
                "parameters": "T2M",
                "community": "AG",
                "longitude": long,
                "latitude": lat,
                "start": start_end,
                "end": start_end,
                "format": "JSON"
            }

            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                daily_data = data["properties"]["parameter"]["T2M"]
                temp_value = list(daily_data.values())[0]
                temps.append(temp_value)
            except Exception as e:
                print(f"Failed to fetch data for {new_date}: {e}")
                temps.append(None)

        # Clean missing data
        temps = [t for t in temps if t is not None]

        if temps:
            avg_temp = sum(temps) / len(temps)
            print(f"Average temperature for {target.strftime('%m-%d')} minus {j} days over past 10 years: {avg_temp:.2f} °C")
        else:
            print(f"No valid data found for {target.strftime('%m-%d')} minus {j} days.")

        all_temps[j] = temps  # store all temps for this day offset

        # now all_temps contains lists of temperatures for each j


temps = getPast10YearsTemps(-74.006, 40.7128, "20250104")

