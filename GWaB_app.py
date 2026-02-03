import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
import folium
import numpy as np
import matplotlib.pyplot as plt
from folium.plugins import Geocoder

from get_GEE import initialize_ee, get_et0, get_rain, get_ndvi
from calculate import calc_irrigation

# initialize_ee()

# DEFAULT_CENTER = [35.26, -119.15]
# DEFAULT_ZOOM = 13

# 🌍 Interactive Map for Coordinate Selection

st.set_page_config(layout='wide')

st.markdown("<h1 style='text-align: center;'>G-WaB: Geographic Water Budget</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; font-size: 20px'>A <a href=\"https://www.bard-isus.org/\"> <strong>BARD</strong></a> research report by: </p>",
    unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center;'><a href=\"mailto:orsp@volcani.agri.gov.il\"> <strong>Or Sperling</strong></a> (ARO-Volcani), <a href=\"mailto:mzwienie@ucdavis.edu\"> <strong>Maciej Zwieniecki</strong></a> (UC Davis), <a href=\"mailto:zellis@ucdavis.edu\"> <strong>Zac Ellis</strong></a> (UC Davis), and <a href=\"mailto:niccolo.tricerri@unito.it\"> <strong>Niccolò Tricerri</strong></a> (UNITO - IUSS Pavia)  </p>",
    unsafe_allow_html=True)

# Center and zoom
map_center = [31.709172, 34.800522]
zoom = 15

# Create map
m = folium.Map(location=map_center, zoom_start=zoom, tiles=None)

folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attr='Map data © Google',
    name='Google Satellite',
    overlay=False,
    control=True
).add_to(m)

m.add_child(folium.LatLngPopup())
Geocoder(collapsed=False, add_marker=False).add_to(m)

map_data = st_folium(m, height=500, width=900, use_container_width=True)


# 🌟 **Streamlit UI**

# 📌 **User Inputs**
# 🌍 Unit system selection

# st.sidebar.caption('This is a research report. For further information contact **Or Sperling** (orsp@volcani.agri.gov.il; ARO-Volcani), **Maciej Zwieniecki** (mzwienie@ucdavis.edu; UC Davis), or **Niccolo Tricerri** (niccolo.tricerri@unito.it; University of Turin).')
st.sidebar.image("img/Marker.png")

use_imperial = st.sidebar.toggle("Use Imperial Units (inches)")

unit_system = "Imperial (inches)" if use_imperial else "Metric (mm)"
unit_label = "inches" if use_imperial else "mm"
conversion_factor = 0.03937 if use_imperial else 1

m_winter = st.sidebar.slider(f"Winter Irrigation ({unit_label})", 0, int(round(700 * conversion_factor)), 0,
                                step=int(round(20 * conversion_factor)),
                                help="Did you irrigate in winter? If yes, how much?")
                                
irrigation_months = st.sidebar.slider("Irrigation Months", 1, 12, (3, 10), step=1,
                                          help="During which months will you irrigate?")


# Layout: 2 columns (map | output)
col2, col1 = st.columns([6, 4])

if map_data and map_data["last_clicked"] is not None and "lat" in map_data["last_clicked"]:
    
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    location = (lat, lon)

    # Fetch and store weather data
    st.session_state["et0"] = get_et0(lat, lon)
    
    rain, latest_date = get_rain(lat, lon)
    st.session_state["rain"] = rain
    
    st.session_state["ndvi"] = get_ndvi(lat, lon)

    # Retrieve stored values
    rain = st.session_state.get("rain")
    ndvi = st.session_state.get("ndvi")
    et0 = st.session_state.get("et0")

    # IF = 0.33 / (1 + np.exp(20 * (ndvi - 0.6))) + 1
    # pNDVI = ndvi * IF
    pNDVI=.8*(1-np.exp(-3*ndvi))

    if rain is not None and ndvi is not None and et0 is not None:

        # 🔄 Always recalculate irrigation when sliders or location change
        df_irrigation = calc_irrigation(pNDVI, rain, et0, m_winter, irrigation_months, 1, conversion_factor)

        total_irrigation = df_irrigation['irrigation'].sum()
        m_irrigation = st.sidebar.slider(f"Water Allocation ({unit_label})", 0,
                                            int(round(1500 * conversion_factor)),
                                            int(total_irrigation), step=int(round(20 * conversion_factor)),
                                            help="Here's the recommended irrigation. Are you constrained by water availability, or considering extra irrigation for salinity management?")

        if m_irrigation>0:
            irrigation_factor = m_irrigation / total_irrigation

            # ✅ Adjust ET0 in the table
            df_irrigation = calc_irrigation(pNDVI, rain, et0, m_winter, irrigation_months, irrigation_factor, conversion_factor)
            total_irrigation = df_irrigation['irrigation'].sum()

        st.markdown(f"""
        <div style='text-align: center; font-size: 30px;'>
            NDVI: {ndvi:.2f} | pNDVI: {pNDVI:.2f} | Rain ({latest_date}): {rain * conversion_factor:.2f} {unit_label}<br>
            ET₀: {df_irrigation['ET0'].sum():.0f} {unit_label} | Irrigation: {total_irrigation:.0f} {unit_label}
        </div>
        """, unsafe_allow_html=True)

        plot_col, table_col = st.columns(2)

        with plot_col:
            # 📈 Plot
            fig, ax = plt.subplots()

            # Filter data for plotting
            start_month, end_month = irrigation_months
            plot_df = df_irrigation[df_irrigation['month'].between(start_month, end_month)].copy()
            plot_df['cumsum_irrigation'] = plot_df['irrigation'].cumsum()

            # plot_df['month'] = pd.to_datetime(plot_df['month'], format='%m')

            # Add drought bars (SW1 = 0) only if they exist
            ax.bar(plot_df.loc[plot_df['SW1'] > 0, 'month'],
                    plot_df.loc[plot_df['SW1'] > 0, 'cumsum_irrigation'], alpha=1, label="Irrigation")

            if (plot_df['SW1'] == 0).any():
                ax.bar(plot_df.loc[plot_df['SW1'] == 0, 'month'],
                        plot_df.loc[plot_df['SW1'] == 0, 'cumsum_irrigation'], alpha=1, label="Deficit Irrigation",
                        color='#FF4B4B')

            # Add a shaded area for SW1 behind the bars
            ax.fill_between(
                plot_df['month'],  # X-axis values (months)
                0,  # Start of the shaded area (baseline)
                plot_df['SW1'],  # End of the shaded area (SW1 values)
                color='#74ac72',  # Green color for the shaded area
                alpha=0.4,  # Transparency
                label="Water Budget"
            )

            # Set plot limits and labels
            ax.set_xlabel("Month")
            ax.set_ylabel(f"Water ({unit_label})")
            ax.legend()

            # Display the plot
            st.pyplot(fig)

        with table_col:
            # 📊 Table
            st.subheader('Monthly Recommendations:')
            
            # Filter by selected irrigation months
            start_month, end_month = irrigation_months
            filtered_df = df_irrigation[df_irrigation['month'].between(start_month, end_month)]

            filtered_df['month'] = pd.to_datetime(filtered_df['month'], format='%m').dt.month_name()
            filtered_df[['ET0', 'irrigation']] = filtered_df[['ET0', 'irrigation']]

            # round ET0 and irrigation to the nearest 5 if units are mm
            if use_imperial:
                filtered_df[['ET0', 'irrigation']] = filtered_df[['ET0', 'irrigation']].round(1)
            else: filtered_df[['ET0', 'irrigation']] = (filtered_df[['ET0', 'irrigation']]/5).round()*5


            st.dataframe(
                filtered_df[['month', 'ET0', 'irrigation', 'alert']]
                .rename(columns={
                    'month': '',
                    'ET0': f'ET₀ ({unit_label})',
                    'irrigation': f'Irrigation ({unit_label})',
                   'alert': 'Alert'
                }).round(1),
                hide_index=True

            )
else: st.markdown("<p style='text-align: center; font-size: 30px;'>Click your field to get started ...</p>", unsafe_allow_html=True)
