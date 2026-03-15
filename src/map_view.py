import streamlit as st
import folium
from folium.plugins import Geocoder
from streamlit_folium import st_folium

_REGIONS = {
    'Israel':     {'center': [31.709172, 34.800522],                    'zoom': 15, 'imperial': False},
    'California': {'center': [35.28372287982474, -119.1700946124702],   'zoom': 14, 'imperial': True},
}


def render_map_section(height=500, width=900):
    """Render map; reads region from session_state['use_california'] set by sidebar toggle."""
    use_california = st.session_state.get('use_california', False)
    region_mode = 'California' if use_california else 'Israel'

    if 'use_imperial' not in st.session_state:
        st.session_state['use_imperial'] = _REGIONS[region_mode]['imperial']

    last_region = st.session_state.get('_last_region_mode')
    if last_region is None:
        st.session_state['_last_region_mode'] = region_mode
    elif last_region != region_mode:
        default_imperial = _REGIONS[region_mode]['imperial']
        for k in list(st.session_state.keys()):
            if k not in {'use_california', '_last_region_mode'}:
                st.session_state.pop(k, None)
        st.session_state['use_imperial'] = default_imperial
        st.session_state['_last_region_mode'] = region_mode
        st.rerun()

    cfg = _REGIONS[region_mode]
    map_data = render_location_map(map_center=cfg['center'], zoom=cfg['zoom'], height=height, width=width)
    clicked = get_clicked_location(map_data)
    if clicked is not None:
        st.session_state['selected_location'] = clicked


def render_location_map(map_center=None, zoom=15, height=500, width=900):
    if map_center is None:
        map_center = [31.709172, 34.800522]

    location_map = folium.Map(location=map_center, zoom_start=zoom, tiles=None)

    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='Map data © Google',
        name='Google Satellite',
        overlay=False,
        control=False,
    ).add_to(location_map)

    location_map.add_child(folium.LatLngPopup())
    Geocoder(collapsed=False, add_marker=False).add_to(location_map)

    return st_folium(location_map, height=height, width=width, use_container_width=True)


def get_clicked_location(map_data):
    if not map_data:
        return None

    last_clicked = map_data.get("last_clicked")
    if not last_clicked:
        return None

    lat = last_clicked.get("lat")
    lon = last_clicked.get("lng")

    if lat is None or lon is None:
        return None

    return lat, lon
