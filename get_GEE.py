import ee
from google.oauth2 import service_account
from datetime import datetime
import streamlit as st
import pandas as pd


# Function to initialize Earth Engine with credentials
def initialize_ee():
    ee.Initialize(project="rsc-gwab-lzp")
    # # Get credentials from Streamlit secrets
    # credentials = service_account.Credentials.from_service_account_info(
    #     st.secrets["gcp_service_account"],
    #     scopes=["https://www.googleapis.com/auth/earthengine"]
    # )
 
initialize_ee()
# ee.Authenticate()
ee.Initialize(project="rsc-gwab-lzp")


# 🌍 Function to Fetch NDVI from Google Earth Engine
@st.cache_data(show_spinner=False)
def get_ndvi(lat, lon):
    poi = ee.Geometry.Point([lon, lat])
    today = datetime.now()
    if today.month < 6:
        today = today.replace(year=today.year - 1)

    img = ee.ImageCollection('COPERNICUS/S2_HARMONIZED') \
        .filterDate(f"{today.year}-05-01", f"{today.year}-06-01") \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
        .median()

    ndvi = img.normalizedDifference(['B8', 'B4']).reduceRegion(
        ee.Reducer.mean(), poi, 50).get('nd').getInfo()

    return round(ndvi, 2) if ndvi else None


@st.cache_data(show_spinner=False)
def get_rain(lat, lon):
    today = datetime.today()
    if today.month < 4:
        today = today.replace(year=today.year - 1)

    poi = ee.Geometry.Point([lon, lat])
    rain_collection = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
        .filterDate(f"{today.year - 1}-11-01", f"{today.year}-04-01")

    rain_sum = rain_collection.sum() \
        .reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=poi,
            scale=5000
        ).get('precipitation')

    # Get the date of the latest image
    latest_image = rain_collection.sort('system:time_start', False).first()
    latest_date = ee.Date(latest_image.get('system:time_start')).format('YYYY-MM-dd').getInfo() if latest_image.getInfo() else None

    return round(rain_sum.getInfo() or 0.0, 1), latest_date


@st.cache_data(show_spinner=False)
def get_et0(lat, lon):
    poi = ee.Geometry.Point([lon, lat])
    dataset = ee.ImageCollection("IDAHO_EPSCOR/TERRACLIMATE") \
        .filterDate("2019-01-01", "2024-12-31") \
        .select('pet')

    stats = ee.FeatureCollection(ee.List.sequence(1, 12).map(
        lambda m: ee.Feature(None, {
            'month': m,
            'ET0': dataset.filter(ee.Filter.calendarRange(m, m, 'month')).mean() \
                .reduceRegion(ee.Reducer.mean(), poi, 4638.3).get('pet')
        })
    )).getInfo()
    
    return pd.DataFrame([{
        'month': int(f['properties']['month']),
        'ET0': round(f['properties']['ET0'] * 0.1 or 0, 2)
    } for f in stats['features']])
