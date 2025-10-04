import streamlit as st
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
import asyncio
from datetime import datetime
from calculate import getExpectedTempAndRainAsync
import time
from geopy.exc import GeocoderTimedOut

# -------------------
# Page setup
# -------------------
st.set_page_config(page_title="NASA Weather Explorer", layout="wide")
st.title("🌍 NASA Weather Explorer")

# -------------------
# Geocoding setup
# -------------------
geolocator = Nominatim(user_agent="streamlit_app", timeout=10)

def geocode_with_retry(location_name, retries=3):
    for _ in range(retries):
        try:
            location = geolocator.geocode(location_name)
            if location:
                return location
        except GeocoderTimedOut:
            time.sleep(1)
    return None

# -------------------
# Layout Containers
# -------------------
main = st.container()

with main:
    left_col, right_col = st.columns([1, 2])  # Map will take more space (right side)

    # -------------------
    # LEFT COLUMN: Inputs + Results
    # -------------------
    with left_col:
        st.subheader("Location & Date")

        location_name = st.text_input("🔍 Search for a location:")
        DISPLAY_YEAR = 2025
        picked_date = st.date_input("📅 Select Day and Month", value=datetime(DISPLAY_YEAR, 1, 1))
        selected_date_display = picked_date.replace(year=DISPLAY_YEAR)

        lat, lon = None, None
        if location_name:
            location = geocode_with_retry(location_name)
            if location:
                lat, lon = location.latitude, location.longitude
            else:
                st.warning("⚠️ Location not found. Try another name.")

        # Placeholder for map click info
        clicked_lat, clicked_lon = None, None

        # Fetch button and weather logic
        if st.button("🚀 Get Weather Forecast", use_container_width=True):
            if lat and lon:
                BACKEND_YEAR = 2020
                selected_date_backend = picked_date.replace(year=BACKEND_YEAR)
                date_str = selected_date_backend.strftime("%Y%m%d")

                async def fetch_weather():
                    return await getExpectedTempAndRainAsync(lat, lon, date_str)

                result = asyncio.run(fetch_weather())

                temp = result.get('expected_temperature')
                rain = result.get('rain_probability')

                st.markdown("---")
                st.subheader("📊 Forecast Results")
                if temp is not None:
                    st.write(f"**Expected Temperature:** {temp:.2f} °C")
                else:
                    st.write("**Expected Temperature:** Data not available")

                if rain is not None:
                    st.write(f"**Rain Probability:** {rain*100:.1f}%")
                else:
                    st.write("**Rain Probability:** Data not available")
            else:
                st.warning("⚠️ Please select or click a location on the map.")

    # -------------------
    # RIGHT COLUMN: Map
    # -------------------
    with right_col:
        st.subheader("🗺️ Map View")

        # Default map
        if lat and lon:
            m = folium.Map(location=[lat, lon], zoom_start=6)
            folium.Marker([lat, lon], popup=location_name).add_to(m)
        else:
            m = folium.Map(location=[20, 0], zoom_start=2)

        # Allow user click to refine location
        m.add_child(folium.LatLngPopup())

        map_data = st_folium(m, width=750, height=500)

        # Update lat/lon if user clicked
        if map_data and map_data["last_clicked"]:
            clicked_lat = map_data["last_clicked"]["lat"]
            clicked_lon = map_data["last_clicked"]["lng"]
            st.info(f"📍 Selected Point: ({clicked_lat:.4f}, {clicked_lon:.4f})")
