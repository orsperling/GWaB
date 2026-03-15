import streamlit as st

st.set_page_config(layout='wide')

from src.get_GEE import initialize_ee, get_et0, get_rain, get_ndvi
from src.calculate import calc_irrigation
from src.map_view import render_map_section
from src.output_view import render_outputs

st.markdown("<h1 style='text-align: center;'>G-WaB: Geographic Water Budget</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; font-size: 20px'>A <a href=\"https://www.bard-isus.org/\"> <strong>BARD</strong></a> research report by: </p>",
    unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center;'><a href=\"mailto:orsp@volcani.agri.gov.il\"> <strong>Or Sperling</strong></a> (ARO-Volcani), <a href=\"mailto:mzwienie@ucdavis.edu\"> <strong>Maciej Zwieniecki</strong></a> (UC Davis), <a href=\"mailto:zellis@ucdavis.edu\"> <strong>Zac Ellis</strong></a> (UC Davis), and <a href=\"mailto:niccolo.tricerri@unito.it\"> <strong>Niccolò Tricerri</strong></a> (UNITO - IUSS Pavia)  </p>",
    unsafe_allow_html=True)

st.sidebar.image("img/Marker.png")
st.sidebar.toggle("California", key='use_california')

render_map_section()


# 🌟 **Streamlit UI**

# 📌 **User Inputs**
# 🌍 Unit system selection

use_imperial = st.sidebar.toggle("Use Imperial Units (inches)", key='use_imperial')

unit_label = "inches" if use_imperial else "mm"
conversion_factor = 0.03937 if use_imperial else 1
                                
irrigation_months = st.sidebar.slider("Irrigation Months", 1, 12, (3, 10), step=1,
                                          help="During which months will you irrigate?")


def init_slider_state(key, default_value, max_value):
    if key not in st.session_state:
        st.session_state[key] = int(round(default_value))
    st.session_state[key] = min(max(0, int(st.session_state[key])), max_value)


selected_location = st.session_state.get('selected_location')

if selected_location is not None:

    lat, lon = selected_location
    location_key = f"{lat:.6f},{lon:.6f}"
    location_changed = st.session_state.get('data_location_key') != location_key

    if location_changed:
        reset_prefixes = ('winter_irrigation_', 'irrigation_limit_')
        reset_keys = {
            'rain_input',
            'winter_irrigation',
            'irrigation_limit',
            'calc_context_key',
            'et0',
            'rain_gee',
            'latest_date',
            'ndvi',
        }
        for session_key in list(st.session_state.keys()):
            if session_key in reset_keys or session_key.startswith(reset_prefixes):
                st.session_state.pop(session_key, None)

    initialize_ee()

    # Fetch and store weather data only when location changes
    if location_changed or any(key not in st.session_state for key in ["et0", "rain_gee", "ndvi", "latest_date"]):
        st.session_state["et0"] = get_et0(lat, lon)
        rain_gee, latest_date = get_rain(lat, lon)
        st.session_state["rain_gee"] = rain_gee
        st.session_state["latest_date"] = latest_date
        st.session_state["ndvi"] = get_ndvi(lat, lon)
        st.session_state["data_location_key"] = location_key

    # Retrieve stored values
    rain_gee = st.session_state.get("rain_gee")
    latest_date = st.session_state.get("latest_date")
    ndvi = st.session_state.get("ndvi")
    et0 = st.session_state.get("et0")

    if rain_gee is not None and ndvi is not None and et0 is not None:

        allocation_max = int(round(1500 * conversion_factor))
        winter_max = int(round(700 * conversion_factor))
        rain_max = int(round(1000 * conversion_factor))
        calc_context_key = f"{lat:.6f},{lon:.6f}|{int(use_imperial)}"

        if st.session_state.get('calc_context_key') != calc_context_key:
            reset_prefixes = ('winter_irrigation_', 'irrigation_limit_')
            for session_key in list(st.session_state.keys()):
                if session_key == 'rain_input' or session_key.startswith(reset_prefixes):
                    st.session_state.pop(session_key, None)
            st.session_state['calc_context_key'] = calc_context_key

        init_slider_state('rain_input', rain_gee * conversion_factor, rain_max)
        rain = st.sidebar.slider(
            f"Rain ({unit_label})",
            0,
            rain_max,
            step=int(round(20 * conversion_factor)),
            key='rain_input',
            help=f"Adjust seasonal rain used in the calculation. Latest GEE rain record: {latest_date if latest_date else 'N/A'}."
        ) / conversion_factor

        # 1) Rain determines recommended winter irrigation
        df_winter_default = calc_irrigation(
            ndvi,
            rain,
            et0,
            irrigation_months,
            0,
            conversion_factor,
            None,
        )
        recommended_winter = int(round(df_winter_default['winter_irrigation'].iloc[0]))
        recommended_winter = min(max(0, recommended_winter), winter_max)

        winter_key = f"winter_irrigation_{calc_context_key}_{int(round(rain * conversion_factor))}"

        winter_irrigation = st.sidebar.slider(
            f"Winter Irrigation ({unit_label})",
            0,
            winter_max,
            value=recommended_winter,
            step=int(round(20 * conversion_factor)),
            key=winter_key,
            help="Estimated from rainfall and soil water capacity."
        )

        # 2) Winter irrigation determines recommended summer irrigation
        df_summer_default = calc_irrigation(
            ndvi,
            rain,
            et0,
            irrigation_months,
            0,
            conversion_factor,
            winter_irrigation,
        )
        recommended_summer = int(round(df_summer_default['summer_irrigation'].iloc[0]))
        recommended_summer = min(max(0, recommended_summer), allocation_max)

        summer_key = f"irrigation_limit_{calc_context_key}_{int(round(rain * conversion_factor))}_{int(round(winter_irrigation))}"

        irrigation_limit = st.sidebar.slider(
            f"Summer Irrigation ({unit_label})",
            0,
            allocation_max,
            value=recommended_summer,
            step=int(round(20 * conversion_factor)),
            key=summer_key,
            help="Here's the recommended irrigation. Are you constrained by water availability, or considering extra irrigation for salinity management?"
        )

        # Recalculate with selected sliders (applies winter/summer changes immediately)
        df_irrigation = calc_irrigation(
            ndvi,
            rain,
            et0,
            irrigation_months,
            irrigation_limit,
            conversion_factor,
            winter_irrigation,
        )
        render_outputs(
            df_irrigation=df_irrigation,
            ndvi=ndvi,
            latest_date=latest_date,
            rain=rain,
            unit_label=unit_label,
            conversion_factor=conversion_factor,
            irrigation_months=irrigation_months,
            winter_irrigation=winter_irrigation,
        )
else: st.markdown("<p style='text-align: center; font-size: 30px;'>Click your field to get started ...</p>", unsafe_allow_html=True)
