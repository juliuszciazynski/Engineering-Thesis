#~~~~~~~~~~~~~~~~~~~~~~~~~~UI~~~~~~~~~~~~~~~~~~~~~~~~~~#
import streamlit as st
import pandas as pd
import sqlite3
#IMPORTING FUNCTIONS AND CONSTANTS
from recommender import (
    get_vacation_recommendations, 
    get_emigration_recommendations, 
    WEATHER_SCALE, 
    ALL_ATTRACTION_GROUPS
)

#WELCOME PAGE
st.set_page_config(page_title="Travel Recommender", page_icon="✈️", layout="wide")


@st.cache_data
def get_language_list():
    """Loads a unique, sorted list of languages from the database."""
    try:
        conn = sqlite3.connect("travel_recommendation_final.db")
        df = pd.read_sql_query("SELECT DISTINCT Language FROM destinations", conn)
        conn.close()
        languages = sorted([lang for lang in df['Language'].unique() if pd.notna(lang) and lang])
        return languages
    except:
        return ['SOMETHING WENT WRONG']

@st.cache_data
def get_countries_and_destinations():
    #COUNTRIES AND DESTINATIONS
    try:
        conn = sqlite3.connect("travel_recommendation_final.db")
        try:
            df = pd.read_sql_query("SELECT Destination, Country_x as Country FROM destinations", conn)
        except pd.io.sql.DatabaseError:
            df = pd.read_sql_query("SELECT Destination, Country FROM destinations", conn)
        conn.close()
        df.dropna(subset=['Destination', 'Country'], inplace=True)
        destinations = sorted(df['Destination'].unique())
        countries = sorted(df['Country'].unique())
        return countries, destinations
    except:
        return ['STH WENT WRONG', 'STH WENT WRONG'], ['STH WENT WRONG', 'STH WENT WRONG']


st.title('Personal Travel Recommender')
st.sidebar.header('Define Your Preferences')

language_options = get_language_list()
country_options, destination_options = get_countries_and_destinations()
#MONTHS TO CHOOSE FROM
month_options = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
#EMIGRATION OR VACATION
mode = st.sidebar.radio("Choose your goal:", ('Vacation', 'Emigration'))
#PLACE EXCLUSION
st.sidebar.subheader("Exclude Places")
excluded_countries = st.sidebar.multiselect('Exclude entire countries:', options=country_options)
excluded_destinations = st.sidebar.multiselect('Exclude specific destinations:', options=destination_options)
final_excluded_list = excluded_countries + excluded_destinations

#UI VACATION
if mode == 'Vacation':
    st.header("Vacation Recommendations")
    
    with st.sidebar:
        #SIDEBARS FOR VACATION
        st.subheader("Main Preferences")
        month_pref = st.selectbox('Select month of travel:', options=month_options, index=6)
        weather_pref = st.selectbox('What kind of weather are you looking for?', options=WEATHER_SCALE, index=5)
        budget_pref = st.select_slider('Select your budget:', options=['Budget', 'MidRange', 'Luxury'], value='MidRange')
        attraction_options = ['everything'] + ALL_ATTRACTION_GROUPS
        attraction_pref = st.multiselect('What types of attractions are you interested in?', options=attraction_options, default=['everything'])
        known_languages_pref = st.multiselect('What other languages do you speak?', options=language_options)
        
        with st.expander("Adjust Model Weights"):
            w_weather = st.slider("Weight: Weather", 0.0, 1.0, 0.25, 0.05, key='w_vac_weather')
            w_budget = st.slider("Weight: Budget", 0.0, 1.0, 0.15, 0.05, key='w_vac_budget')
            w_attr_quantity = st.slider("Weight: Attraction Quantity", 0.0, 1.0, 0.10, 0.05, key='w_vac_attr_qnt')
            w_attr_quality = st.slider("Weight: Attraction Quality", 0.0, 1.0, 0.15, 0.05, key='w_vac_attr_ql')
            w_safety = st.slider("Weight: Safety", 0.0, 1.0, 0.10, 0.05, key='w_vac_safety')
            w_attr_pop = st.slider(
                'Weight: Popularity (negative = less crowded)',
                -1.0, 1.0, 0.05, 0.05, key='w_vac_attr_pop'
            )
            w_eng_level = st.slider("Weight: English Level", 0.0, 1.0, 0.05, 0.05, key='w_vac_eng')
            w_known_lang = st.slider("Weight: Known Languages", 0.0, 1.0, 0.05, 0.05, key='w_vac_lang')
            w_distance = st.slider("Weight: Distance", 0.0, 1.0, 0.05, 0.05, key='w_vac_dist')
            w_cuisine = st.slider("Weight: Cuisine Quality", 0.0, 1.0, 0.10, 0.05, key='w_vac_cuisine')

    if st.button('Find my perfect vacation!'):
        if not attraction_pref:
            st.sidebar.error("Please select at least one attraction type (or 'everything').")
        else:
            vacation_preferences = {
                'month': month_pref,
                'weather': weather_pref,
                'budget': budget_pref,
                'attractions': attraction_pref,
                'known_languages': known_languages_pref,
                'excluded_places': final_excluded_list
            }
            vacation_weights = {
                'weather': w_weather, 'budget': w_budget, 'attractions_quantity': w_attr_quantity, 
                'attractions_quality': w_attr_quality, 'safety': w_safety, 
                'attractions_popularity': w_attr_pop, 'english_level': w_eng_level, 
                'known_languages': w_known_lang, 'distance': w_distance, 'cuisine_quality': w_cuisine
            }
            
            with st.spinner('Thinking...'):
                recommendations = get_vacation_recommendations(vacation_preferences, vacation_weights)
                st.success('Done!')
                if recommendations is not None and not recommendations.empty:
                    recommendations.rename(columns={'Country_x': 'Country'}, inplace=True)
                    st.dataframe(recommendations)
                else:
                    st.error("No recommendations found for the given criteria.")

#UI Emigration---
elif mode == 'Emigration':
    st.header("Emigration Recommendations")
    #SAME AS BEFORE
    with st.sidebar:
        st.subheader("Main Preferences")
        weather_pref_em = st.selectbox('What climate do you prefer year-round?', options=WEATHER_SCALE, index=4, key='weather_em')
        known_languages_pref_em = st.multiselect('What other languages do you speak?', options=language_options, key='lang_em')
        
        with st.expander("Adjust Model Weights"):
            w_cost_living = st.slider("Weight: Cost of Living", 0.0, 1.0, 0.25, 0.05, key='w_em_cost')
            w_purchasing_power = st.slider("Weight: Purchasing Power", 0.0, 1.0, 0.25, 0.05, key='w_em_power')
            w_safety_em = st.slider("Weight: Safety", 0.0, 1.0, 0.10, 0.05, key='w_em_safety')
            w_eng_level_em = st.slider("Weight: English Level", 0.0, 1.0, 0.10, 0.05, key='w_em_eng')
            w_hdi = st.slider("Weight: HDI", 0.0, 1.0, 0.10, 0.05, key='w_em_hdi')
            w_unemployment = st.slider("Weight: Unemployment", 0.0, 1.0, 0.05, 0.05, key='w_em_unemp')
            w_inflation = st.slider("Weight: Inflation", 0.0, 1.0, 0.05, 0.05, key='w_em_infl')
            w_life_exp = st.slider("Weight: Life Expectancy", 0.0, 1.0, 0.05, 0.05, key='w_em_life')
            w_distance_em = st.slider("Weight: Distance", 0.0, 1.0, 0.0, 0.05, key='w_em_dist')
            w_weather_em = st.slider("Weight: Weather", 0.0, 1.0, 0.05, 0.05, key='w_em_weather')
            w_known_lang_em = st.slider("Weight: Known Languages", 0.0, 1.0, 0.05, 0.05, key='w_em_lang')

    if st.button('Find the best place to live!'):
        emigration_preferences = {
            'weather': weather_pref_em,
            'known_languages': known_languages_pref_em,
            'excluded_places': final_excluded_list
        }
        emigration_weights = {
            'cost_of_living': w_cost_living, 'purchasing_power': w_purchasing_power, 
            'safety': w_safety_em, 'english_level': w_eng_level_em, 'hdi': w_hdi, 
            'unemployment': w_unemployment, 'inflation': w_inflation, 
            'life_expectancy': w_life_exp, 'distance': w_distance_em,
            'weather': w_weather_em, 'known_languages': w_known_lang_em
        }
        
        with st.spinner('Thinking...'):
            recommendations = get_emigration_recommendations(emigration_preferences, emigration_weights)
            st.success('Done!')
            if recommendations is not None and not recommendations.empty:
                st.dataframe(recommendations)
            else:
                st.error("No recommendations found for the given criteria.")