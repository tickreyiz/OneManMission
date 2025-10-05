# POWER-ed: NASA Weather Estimation Tool

**POWER-ed** is a lightweight web application that provides user-friendly access to NASA’s POWER climate data.  
It fetches 10 years of historical temperature and precipitation data for any location and date, then applies machine learning to estimate the expected temperature and probability of rain.

This project was **entirely designed and developed by a single developer in just 2 days** for the **2025 NASA Space Apps Challenge**.

- [Project Demo](https://www.youtube.com/watch?v=eOwu1O-hj1k)  
- [Project Link](https://www.spaceappschallenge.org/2025/find-a-team/onemanmission/)

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/tickreyiz/power-ed.git
cd power-ed

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run lit.py

# Then open your browswer and type this
http://localhost:8501
```
## How It Works

Data Retrieval: Fetches NASA POWER data for temperature (T2M) and precipitation (PRECTOTCORR).

Historical Scope: Gathers data for the last 10 years for the selected coordinates and date.

Modeling:

-Temperature is estimated using linear regression.

-Rain probability is calculated as the percentage of rainy days (>1mm of precipitation).

Smoothing: Includes data ±4 days around the target date to reduce noise and improve accuracy.

Interface: Built with Streamlit and Leaflet/Folium, providing an interactive experience for users to select any global location and visualize results.

Lightweight Deployment: The app runs fully on API calls — no database — making it simple to host and maintain.
