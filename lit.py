import streamlit as st
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import nest_asyncio
import asyncio
from datetime import datetime
import pandas as pd
import altair as alt

from test import get_expected_temp_and_rain  # updated safe function

# -------------------
# Streamlit setup
# -------------------
nest_asyncio.apply()
st.set_page_config(page_title="NASA Weather Explorer", layout="wide")
st.title("🌍 NASA Weather Explorer")

# -------------------
# Geocoder setup
# -------------------
geolocator = Nominatim(user_agent="streamlit_app", timeout=10)

@st.cache_data(show_spinner=False)
def geocode_with_retry(location_name, retries=3):
    for _ in range(retries):
        try:
            location = geolocator.geocode(location_name)
            if location:
                return location
        except GeocoderTimedOut:
            continue
    return None

# -------------------
# Async weather fetcher wrapper
# -------------------
def fetch_weather(lat: float, lon: float, date_str: str):
    async def inner():
        return await get_expected_temp_and_rain(lat, lon, date_str, return_history=True)
    return asyncio.get_event_loop().run_until_complete(inner())

# -------------------
# Categorization functions
# -------------------
def categorize_temperature(temp):
    if temp is None:
        return "Data not available"
    elif temp < 0:
        return "❄️ Very Cold"
    elif 0 <= temp < 10:
        return "🥶 Cold"
    elif 10 <= temp < 20:
        return "🌤️ Mild"
    elif 20 <= temp < 30:
        return "🌞 Warm"
    else:
        return "🔥 Very Hot"

def categorize_rain(rain_prob):
    if rain_prob is None:
        return "Data not available"
    elif rain_prob < 0.1:
        return "☀️ Very Dry"
    elif 0.1 <= rain_prob < 0.3:
        return "🌤️ Slight Chance of Rain"
    elif 0.3 <= rain_prob < 0.6:
        return "🌧️ Likely Rain"
    else:
        return "⛈️ Very Wet"

# -------------------
# Initialize session_state
# -------------------
if "lat" not in st.session_state:
    st.session_state.lat = None
if "lon" not in st.session_state:
    st.session_state.lon = None
if "location_name" not in st.session_state:
    st.session_state.location_name = None
if "fetch_weather" not in st.session_state:
    st.session_state.fetch_weather = False

# -------------------
# Layout
# -------------------
left_col, right_col = st.columns([1, 2])

# --- LEFT COLUMN: Inputs & Forecast ---
with right_col:
    st.subheader("📍 Location & Date")

    # Location input (allow coordinates as well)
    location_input = st.text_input(
        "🔍 Search for a location or enter coordinates (lat, lon):",
        value=st.session_state.location_name or ""
    )
    picked_date = st.date_input("📅 Select Day and Month", value=datetime(2025, 1, 1))

    if location_input:
        # Only update session state if manually typed
        if location_input != st.session_state.location_name:
            try:
                lat_str, lon_str = location_input.split(",")
                lat, lon = float(lat_str.strip()), float(lon_str.strip())
                st.session_state.lat = lat
                st.session_state.lon = lon
                st.session_state.location_name = f"{lat}, {lon}"
            except ValueError:
                location = geocode_with_retry(location_input)
                if location:
                    st.session_state.lat = location.latitude
                    st.session_state.lon = location.longitude
                    st.session_state.location_name = location_input
                else:
                    st.error("❌ Location not found. Try another name or coordinates.")

    # Fetch weather button
    if st.button("🚀 Get Weather Forecast", use_container_width=True):
        if st.session_state.lat and st.session_state.lon:
            st.session_state.fetch_weather = True
        else:
            st.warning("⚠️ Please enter a valid location or coordinates first.")

    # Display forecast results
    if st.session_state.fetch_weather and st.session_state.lat and st.session_state.lon:
        BACKEND_REFERENCE_YEAR = 2020
        date_str = picked_date.replace(year=BACKEND_REFERENCE_YEAR).strftime("%Y%m%d")
        with st.spinner("Fetching NASA weather data..."):
            try:
                temp, rain_prob, history = fetch_weather(st.session_state.lat, st.session_state.lon, date_str)
            except Exception as e:
                st.error(f"⚠️ Error fetching weather data: {e}")
                st.stop()

        st.markdown("---")
        st.subheader("📊 Forecast Results")
        st.write(f"🌡️ **Temperature:** {categorize_temperature(temp)} ({temp:.2f} °C)")
        st.write(f"🌧️ **Rain Probability:** {categorize_rain(rain_prob)} ({rain_prob*100:.1f}%)")

        if history:
            df = pd.DataFrame(history)
            df_temp = df[df['temp'].notna()]
            avg_per_year = df_temp.groupby('year')['temp'].mean().reset_index()

            chart = alt.Chart(avg_per_year).mark_line(point=True).encode(
                x=alt.X('year:O', title='Year'),
                y=alt.Y('temp:Q', title='Average Temperature (°C)'),
                tooltip=['year', 'temp']
            ).properties(
                width=700,
                height=400,
                title='🌡️ Average Temperature ±4 Days by Year'
            )
            st.altair_chart(chart, use_container_width=True)
        st.session_state.fetch_weather = False

# --- RIGHT COLUMN: Map ---
with left_col:
    st.subheader("🗺️ Map View")
    map_center = [st.session_state.lat, st.session_state.lon] if st.session_state.lat else [20, 0]
    zoom = 6 if st.session_state.lat else 2

    m = folium.Map(location=map_center, zoom_start=zoom)
    if st.session_state.lat:
        folium.Marker(
            [st.session_state.lat, st.session_state.lon],
            popup=st.session_state.location_name
        ).add_to(m)

    # Map interaction: update search box but do NOT fetch automatically
    map_data = st_folium(m, width=750, height=500)
    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]

        # Update search box and session_state
        st.session_state.location_name = f"{clicked_lat:.6f}, {clicked_lon:.6f}"
        st.session_state.lat = clicked_lat
        st.session_state.lon = clicked_lon
        st.rerun()
        # No rerun, no automatic fetch

st.markdown("---")
st.markdown('<p style="text-align:center; color:gray; font-size:12px;">Made with ❤️ by TickReyiz</p>', unsafe_allow_html=True)
