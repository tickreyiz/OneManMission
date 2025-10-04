import streamlit as st
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import nest_asyncio
import asyncio
from datetime import datetime
from calculate import getExpectedTempAndRainAsync

# -------------------
# Core setup
# -------------------
nest_asyncio.apply()  # allow asyncio inside Streamlit
st.set_page_config(page_title="NASA Weather Explorer", layout="wide")
st.title("🌍 NASA Weather Explorer")

# -------------------
# Geocoder setup
# -------------------
geolocator = Nominatim(user_agent="streamlit_app", timeout=10)

@st.cache_data(show_spinner=False)
def geocode_with_retry(location_name, retries=3):
    """Try geocoding a location several times before failing."""
    for _ in range(retries):
        try:
            location = geolocator.geocode(location_name)
            if location:
                return location
        except GeocoderTimedOut:
            continue
    return None


# -------------------
# Async weather fetching
# -------------------
def fetch_weather(lat: float, lon: float, date_str: str):
    """Run async NASA weather fetcher safely inside Streamlit."""
    async def inner():
        return await getExpectedTempAndRainAsync(lat, lon, date_str)
    return asyncio.get_event_loop().run_until_complete(inner())


# -------------------
# Page Layout
# -------------------
left_col, right_col = st.columns([1, 2])  # Input left, Map right

with left_col:
    st.subheader("📍 Location & Date")

    # Inputs
    location_name = st.text_input("🔍 Search for a location:")
    picked_date = st.date_input("📅 Select Day and Month", value=datetime(2025, 1, 1))

    # Initialize coords
    lat, lon = None, None

    # Try geocoding user input
    if location_name:
        location = geocode_with_retry(location_name)
        if location:
            lat, lon = location.latitude, location.longitude
        else:
            st.error("❌ Location not found. Try another name.")

    # Fetch button
    if st.button("🚀 Get Weather Forecast", use_container_width=True):
        if lat and lon:
            BACKEND_REFERENCE_YEAR = 2020  # NASA dataset year
            selected_date_backend = picked_date.replace(year=BACKEND_REFERENCE_YEAR)
            date_str = selected_date_backend.strftime("%Y%m%d")

            with st.spinner("Fetching NASA weather data..."):
                try:
                    result = fetch_weather(lat, lon, date_str)
                except Exception as e:
                    st.error(f"⚠️ Error fetching weather data: {e}")
                    st.stop()

            temp = result.get("expected_temperature")
            rain = result.get("rain_probability")

            st.markdown("---")
            st.subheader("📊 Forecast Results")

            if temp is not None:
                st.write(f"🌡️ **Expected Temperature:** {temp:.2f} °C")
            else:
                st.write("🌡️ **Expected Temperature:** Data not available")

            if rain is not None:
                st.write(f"🌧️ **Rain Probability:** {rain*100:.1f}%")
            else:
                st.write("🌧️ **Rain Probability:** Data not available")

        else:
            st.warning("⚠️ Please enter a location or click a point on the map.")


with right_col:
    st.subheader("🗺️ Map View")

    # Default map or zoom to selected point
    if lat and lon:
        m = folium.Map(location=[lat, lon], zoom_start=6)
        folium.Marker([lat, lon], popup=location_name or "Selected Point").add_to(m)
    else:
        m = folium.Map(location=[20, 0], zoom_start=2)

    # Enable clicking to get coordinates
    m.add_child(folium.LatLngPopup())
    map_data = st_folium(m, width=750, height=500)

    # If user clicks on the map
    if map_data and map_data["last_clicked"]:
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]
        st.info(f"📍 Selected Point: ({clicked_lat:.4f}, {clicked_lon:.4f})")

        # Automatically show forecast for clicked point
        if st.button("🌤️ Get Weather for Clicked Point", use_container_width=True):
            BACKEND_REFERENCE_YEAR = 2020
            selected_date_backend = picked_date.replace(year=BACKEND_REFERENCE_YEAR)
            date_str = selected_date_backend.strftime("%Y%m%d")

            with st.spinner("Fetching NASA weather data..."):
                try:
                    result = fetch_weather(clicked_lat, clicked_lon, date_str)
                except Exception as e:
                    st.error(f"⚠️ Error fetching weather data: {e}")
                    st.stop()

            temp = result.get("expected_temperature")
            rain = result.get("rain_probability")

            st.markdown("---")
            st.subheader("📊 Forecast Results")

            if temp is not None:
                st.write(f"🌡️ **Expected Temperature:** {temp:.2f} °C")
            else:
                st.write("🌡️ **Expected Temperature:** Data not available")

            if rain is not None:
                st.write(f"🌧️ **Rain Probability:** {rain*100:.1f}%")
            else:
                st.write("🌧️ **Rain Probability:** Data not available")
