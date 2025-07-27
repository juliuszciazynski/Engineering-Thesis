import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="Map Test", layout="wide")
st.title("Map Functionality Test")

# Create simple, hardcoded data for the test
test_data = {
    'Rank': [1, 2, 3],
    'Destination': ['Paris', 'Rome', 'Warsaw'],
    'Country': ['France', 'Italy', 'Poland'],
    'lat': [48.8566, 41.9028, 52.2297],
    'lon': [2.3522, 12.4964, 21.0122]
}
df_test = pd.DataFrame(test_data)

st.write("Test Data:")
st.dataframe(df_test)

st.subheader("Test Map with Numbered Pins")

try:
    view_state = pdk.ViewState(
        latitude=df_test['lat'].mean(),
        longitude=df_test['lon'].mean(),
        zoom=3.5,
        pitch=40
    )

    text_layer = pdk.Layer(
        "TextLayer",
        data=df_test,
        get_position=['lon', 'lat'],
        get_text='Rank',
        get_color=[0, 0, 0, 200],  # Black text
        get_size=18,
        get_background_color=[255, 255, 255, 180],  # White background
        get_border_color=[0, 0, 0],
        get_border_width=1,
    )

    deck = pdk.Deck(
        layers=[text_layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v10',
        tooltip={"text": "{Destination}, {Country}"}
    )

    st.pydeck_chart(deck)
    st.success("PyDeck chart rendered successfully.")

except Exception as e:
    st.error(f"An error occurred while rendering the PyDeck chart: {e}")