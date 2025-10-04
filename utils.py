import requests

def fetch_temp(long, lat, date_str):
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
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        daily_data = data["properties"]["parameter"]["T2M"]
        return list(daily_data.values())[0]
    except Exception as e:
        print(f"Failed to fetch temperature for {date_str}: {e}")
        return None


# Example for a single date
longitude = -122.4194
latitude = 37.7749
dates = ["2023-10-01", "2023-10-02", "2023-10-03"]  # valid historical dates

temperatures = [fetch_temp(longitude, latitude, d) for d in dates]

for d, temp in zip(dates, temperatures):
    print(f"{d}: {temp}°C")
