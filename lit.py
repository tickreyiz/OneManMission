import streamlit as st
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import nest_asyncio
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import altair as alt

from test import get_expected_temp_and_rain  # updated safe function


# -------------------
# Helpers
# -------------------
def reset_fetch_state():
    st.session_state.fetch_weather = False
    st.session_state.isWorking = False


# -------------------
# Streamlit setup
# -------------------
nest_asyncio.apply()
st.set_page_config(page_title="POWER-ed", layout="wide")
st.title("🌍 POWER-ed")

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
# Categorization
# -------------------
def categorize_temperature(temp):
    if temp is None:
        return "Oops! Data not available ❌"
    elif temp < 0:
        return "❄️ Very Cold — Bundle up and stay warm!"
    elif 0 <= temp < 10:
        return "🥶 Cold — A cozy jacket or hot drink would be nice."
    elif 10 <= temp < 20:
        return "🌤️ Mild — Perfect for a light sweater and a stroll outside."
    elif 20 <= temp < 30:
        return "🌞 Warm — Great weather for outdoor activities, stay hydrated!"
    else:
        return "🔥 Very Hot — Keep cool, wear light clothes, and drink plenty of water."

def categorize_rain(rain_prob):
    if rain_prob is None:
        return "Oops! Data not available ❌"
    elif rain_prob < 0.1:
        return "☀️ Very Dry — Perfect day to enjoy the sun!"
    elif 0.1 <= rain_prob < 0.3:
        return "🌤️ Slight Chance of Rain — You might want to carry a light umbrella just in case."
    elif 0.3 <= rain_prob < 0.6:
        return "🌧️ Likely Rain — Don't forget your umbrella or raincoat!"
    else:
        return "⛈️ Very Wet — Stay indoors if possible, or be prepared for heavy rain!"


# -------------------
# Initialize session_state
# -------------------
defaults = {
    "lat": None,
    "lon": None,
    "location_name": None,
    "fetch_weather": False,
    "isWorking": False,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# -------------------
# Layout
# -------------------
left_col, right_col = st.columns([1, 2])

# --- RIGHT COLUMN ---
with right_col:
    st.subheader("📍 Location & Date")

    location_input = st.text_input(
        "🔍 Search for a location or enter coordinates (lat, lon):",
        value=st.session_state.location_name or ""
    )
    picked_date = st.date_input("📅 Select Day and Month", value=datetime(2025, 1, 1))

    if location_input:
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

    # 🚀 Fetch button
    if st.button("🚀 Get Weather Likelihood", use_container_width=True, disabled=st.session_state.isWorking):
        if st.session_state.lat and st.session_state.lon:
            st.session_state.isWorking = True  # Disable button
            st.session_state.fetch_weather = True
            st.rerun()
        else:
            st.warning("⚠️ Please enter a valid location or coordinates first.")

    # 🌦️ Fetch results
    if st.session_state.fetch_weather and st.session_state.lat and st.session_state.lon:
        BACKEND_REFERENCE_YEAR = datetime.now().year - 1
        date_str = picked_date.replace(year=BACKEND_REFERENCE_YEAR).strftime("%Y%m%d")

        with st.spinner("Fetching NASA POWER data..."):
            try:
                # Check if user is currently rate-limited
                if "rate_limited_until" in st.session_state:
                    if datetime.now() < st.session_state.rate_limited_until:
                        remaining = (st.session_state.rate_limited_until - datetime.now()).seconds
                        st.warning(f"🚫 Rate limit active. Please wait {remaining} seconds.")
                        reset_fetch_state()
                        st.stop()

                temp, rain_prob, history = fetch_weather(
                    st.session_state.lat, st.session_state.lon, date_str
                )

            except Exception as e:
                msg = str(e).lower()
                if "rate limit" in msg or "429" in msg or "too many requests" in msg:
                    st.session_state.rate_limited_until = datetime.now() + timedelta(minutes=1)
                    st.error("🚫 NASA API rate limit hit. Please wait 1 minute before trying again.")
                else:
                    st.error(f"⚠️ Error fetching weather data: {e}")
                reset_fetch_state()
                st.stop()
        # ✅ İşlem tamamlandı
        reset_fetch_state()

        st.markdown("---")
        st.subheader("📊 Estimated Likelihood")
        st.markdown(
            f"<p style='font-size:24px;'>🌡️ Temperature: {categorize_temperature(temp)} ({temp:.2f} °C)</p>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<p style='font-size:24px;'>🌧️ Rain Probability: {categorize_rain(rain_prob)} ({rain_prob*100:.1f}%)</p>",
            unsafe_allow_html=True
        )

        if st.button("OK"):
            st.rerun()

        if history:
            df = pd.DataFrame(history)
            
            # Separate temperature and rain data
            df_temp = df[df['temp'].notna()].copy()
            df_rain = df[df['rain'].notna()].copy()
            
            # Calculate averages per year for temperature
            avg_temp = df_temp.groupby('year')['temp'].mean().reset_index()
            
            if not df_rain.empty:
                # Convert rain to probability (rain >= 1mm means rain occurred)
                df_rain['rain_occurred'] = (df_rain['rain'] >= 1).astype(int)
                avg_rain_prob = df_rain.groupby('year')['rain_occurred'].mean().reset_index()
                avg_rain_prob.rename(columns={'rain_occurred': 'rain_prob'}, inplace=True)
                
                # Merge temperature and rain data
                avg_per_year = pd.merge(avg_temp, avg_rain_prob, on='year', how='outer')
                
                # Create base chart
                base = alt.Chart(avg_per_year).encode(
                    x=alt.X('year:O', title='Year')
                )

                # Temperature line (left axis)
                temp_line = base.mark_line(point=True, color='#FF6B6B', size=3).encode(
                    y=alt.Y('temp:Q', title='Average Temperature (°C)', axis=alt.Axis(titleColor='#FF6B6B')),
                    tooltip=[
                        alt.Tooltip('year:O', title='Year'),
                        alt.Tooltip('temp:Q', title='Temperature (°C)', format='.2f')
                    ]
                )

                # Rain line (right axis)
                rain_line = base.mark_line(point=True, color='#4ECDC4', strokeDash=[5, 5], size=3).encode(
                    y=alt.Y('rain_prob:Q', title='Rain Probability (%)', 
                            axis=alt.Axis(titleColor='#4ECDC4', format='%')),
                    tooltip=[
                        alt.Tooltip('year:O', title='Year'),
                        alt.Tooltip('rain_prob:Q', title='Rain Probability', format='.1%')
                    ]
                )

                # Combine with dual axis
                chart = alt.layer(temp_line, rain_line).resolve_scale(
                    y='independent'
                ).properties(
                    width=700,
                    height=400,
                    title='🌡️ Temperature & 🌧️ Rain Probability ±4 Days by Year'
                )
            else:
                # Only temperature data available
                chart = alt.Chart(avg_temp).mark_line(point=True).encode(
                    x=alt.X('year:O', title='Year'),
                    y=alt.Y('temp:Q', title='Average Temperature (°C)'),
                    tooltip=['year', 'temp']
                ).properties(
                    width=700,
                    height=400,
                    title='🌡️ Average Temperature ±4 Days by Year'
                )
            
            st.altair_chart(chart, use_container_width=True)


# --- LEFT COLUMN ---
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

    map_data = st_folium(m, width=750, height=500)
    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]
        st.session_state.location_name = f"{clicked_lat:.6f}, {clicked_lon:.6f}"
        st.session_state.lat = clicked_lat
        st.session_state.lon = clicked_lon
        st.rerun()

st.markdown("---")
st.markdown('<p style="text-align:center; color:gray; font-size:12px;">Made with ❤️ by TickReyiz</p>', unsafe_allow_html=True)
