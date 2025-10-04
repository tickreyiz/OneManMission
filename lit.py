import streamlit as st
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import nest_asyncio
import asyncio
from datetime import datetime
from test import get_expected_temp_and_rain  # your async function

# Allow asyncio inside Streamlit
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
        return await get_expected_temp_and_rain(lat, lon, date_str)
    return asyncio.get_event_loop().run_until_complete(inner())

# -------------------
# Layout
# -------------------
left_col, right_col = st.columns([1, 2])

with left_col:
    st.subheader("📍 Location & Date")
    location_name = st.text_input("🔍 Search for a location:")
    picked_date = st.date_input("📅 Select Day and Month", value=datetime(2025, 1, 1))

    lat, lon = None, None
    if location_name:
        location = geocode_with_retry(location_name)
        if location:
            lat, lon = location.latitude, location.longitude
        else:
            st.error("❌ Location not found. Try another name.")

    if st.button("🚀 Get Weather Forecast", use_container_width=True):
        if lat and lon:
            BACKEND_REFERENCE_YEAR = 2020
            selected_date_backend = picked_date.replace(year=BACKEND_REFERENCE_YEAR)
            date_str = selected_date_backend.strftime("%Y%m%d")
            with st.spinner("Fetching NASA weather data..."):
                try:
                    temp, rain_prob = fetch_weather(lat, lon, date_str)
                except Exception as e:
                    st.error(f"⚠️ Error fetching weather data: {e}")
                    st.stop()

            st.markdown("---")
            st.subheader("📊 Forecast Results")
            st.write(f"🌡️ **Expected Temperature:** {temp:.2f} °C" if temp else "Data not available")
            if rain_prob is not None:
                st.write(f"🌧️ **Rain Probability:** {rain_prob*100:.1f}%")
            else:
                st.write("🌧️ **Rain Probability:** Data not available")
        else:
            st.warning("⚠️ Please enter a location or click a point on the map.")

with right_col:
    st.subheader("🗺️ Map View")
    if lat and lon:
        m = folium.Map(location=[lat, lon], zoom_start=6)
        folium.Marker([lat, lon], popup=location_name or "Selected Point").add_to(m)
    else:
        m = folium.Map(location=[20, 0], zoom_start=2)

    m.add_child(folium.LatLngPopup())
    map_data = st_folium(m, width=750, height=500)

    # Handle map clicks
    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]
        st.info(f"📍 Selected Point: ({clicked_lat:.4f}, {clicked_lon:.4f})")

        if st.button("🌤️ Get Weather for Clicked Point", use_container_width=True):
            date_str = picked_date.strftime("%Y%m%d")
            with st.spinner("Fetching NASA weather data..."):
                try:
                    temp, rain_prob = fetch_weather(clicked_lat, clicked_lon, date_str)
                except Exception as e:
                    st.error(f"⚠️ Error fetching weather data: {e}")
                    st.stop()

            st.markdown("---")
            st.subheader("📊 Forecast Results")
            st.write(f"🌡️ **Expected Temperature:** {temp:.2f} °C" if temp else "Data not available")
            st.write(f"🌧️ **Rain Probability:** {rain_prob*100:.1f}%" if rain_prob else "Data not available")
