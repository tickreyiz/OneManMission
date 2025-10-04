import streamlit as st
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
import asyncio
from calculate import getExpectedTempAndRainAsync

st.title("Weather Explorer")

# Initialize geocoder
geolocator = Nominatim(user_agent="streamlit_app",timeout=10)

# Search bar for location
location_name = st.text_input("Search for a location:")

lat, lon = None, None
if location_name:
    try:
        location = geolocator.geocode(location_name)
        if location:
            lat, lon = location.latitude, location.longitude
        else:
            st.warning("Location not found. Try another name.")
    except Exception as e:
        st.error(f"Geocoding error: {e}")

# Create a map
if lat and lon:
    m = folium.Map(location=[lat, lon], zoom_start=6)
    folium.Marker([lat, lon], popup=location_name).add_to(m)
else:
    # Default map if no search
    m = folium.Map(location=[20, 0], zoom_start=2)

# Display the map
map_data = st_folium(m, width=700, height=500)

# Use the found coordinates for weather fetch
if lat and lon:
    st.write(f"Selected Location: {location_name} (Lat: {lat:.4f}, Lon: {lon:.4f})")
    
    if st.button("Get Weather Forecast"):
        async def fetch_weather():
            return await getExpectedTempAndRainAsync(lat, lon, "20250101")
        
        result = asyncio.run(fetch_weather())

        temp = result.get('expected_temperature')
        if temp is not None:
            st.write(f"**Expected Temperature:** {temp:.2f} °C")
        else:
            st.write("**Expected Temperature:** Data not available")

        rain = result.get('rain_probability')
        if rain is not None:
            st.write(f"**Rain Probability:** {rain*100:.1f}%")
        else:
            st.write("**Rain Probability:** Data not available")
