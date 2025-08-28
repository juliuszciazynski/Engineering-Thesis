import streamlit as st
import pandas as pd
import sqlite3
import re
import folium
from streamlit_folium import st_folium

#IMPORTING FUNCTIONS AND CONSTANTS from other FILES
from recommender import (
    get_vacation_recommendations, 
    get_emigration_recommendations, 
    WEATHER_SCALE, 
    ALL_ATTRACTION_GROUPS
)

#WELCOME PAGE
st.set_page_config(page_title="Travel Recommender", page_icon="✈️", layout="wide")


# --- Preset Dictionaries ---
VACATION_PRESETS = {
    "Balanced": { 'weather': 0.3, 'budget': 0.3, 'attractions_quantity': 0.3, 'attractions_quality': 0.30, 'safety': 0.20, 'attractions_popularity': 0.10, 'english_level': 0.25, 'known_languages': 0.20, 'distance': 0.05, 'cuisine_quality': 0.15 },
    "Budget Explorer": { 'weather': 0.3, 'budget': 0.6, 'attractions_quantity': 0.3, 'attractions_quality': 0.1, 'safety': 0.1, 'attractions_popularity': 0.05, 'english_level': 0.2, 'known_languages': 0.3, 'distance': 0.15, 'cuisine_quality': 0.20 },
    "Culture & Cuisine Connoisseur": { 'weather': 0.1, 'budget': 0.0, 'attractions_quantity': 0.2, 'attractions_quality': 0.5, 'safety': 0.20, 'attractions_popularity': 0.1, 'english_level': 0.2, 'known_languages': 0.3, 'distance': 0.0, 'cuisine_quality': 0.6 },
    "Off-Grid Adventurer": { 'weather': 0.3, 'budget': 0.2, 'attractions_quantity': 0.3, 'attractions_quality': 0.1, 'safety': 0.1, 'attractions_popularity': -0.5, 'english_level': 0.2, 'known_languages': 0.0, 'distance': 0.0, 'cuisine_quality': 0.1},
    "Family Vacation": { 'weather': 0.5, 'budget': 0.25, 'attractions_quantity': 0.5, 'attractions_quality': 0.4, 'safety': 0.3, 'attractions_popularity': 0.4, 'english_level': 0.05, 'known_languages': 0.05, 'distance': 0.2, 'cuisine_quality': 0.3 }
}


EMIGRATION_PRESETS = {
    "Balanced": { 'cost_of_living': 0.20, 'purchasing_power': 0.20, 'safety': 0.10, 'english_level': 0.10, 'hdi': 0.10, 'unemployment': 0.10, 'inflation': 0.05, 'life_expectancy': 0.05, 'distance': 0.05, 'weather': 0.05, 'known_languages': 0.05 },
    "Young Professional": { 'cost_of_living': 0.15, 'purchasing_power': 0.5, 'safety': 0.05, 'english_level': 0.3, 'hdi': 0.05, 'unemployment': 0.2, 'inflation': 0.1, 'life_expectancy': 0.0, 'distance': 0.0, 'weather': 0.0, 'known_languages': 0.4 },
    "The Family": { 'cost_of_living': 0.3, 'purchasing_power': 0.1, 'safety': 0.3, 'english_level': 0.05, 'hdi': 0.2, 'unemployment': 0.2, 'inflation': 0.2, 'life_expectancy': 0.2, 'distance': 0.1, 'weather': 0.1, 'known_languages': 0.0 },
    "Digital Nomad": { 'cost_of_living': 0.5, 'purchasing_power': 0.0, 'safety': 0.2, 'english_level': 0.3, 'hdi': 0.0, 'unemployment': 0.0, 'inflation': 0.1, 'life_expectancy': 0.0, 'distance': 0.0, 'weather': 0.3, 'known_languages': 0.0 },
    "Retiree": { 'cost_of_living': 0.4, 'purchasing_power': 0.1, 'safety': 0.3, 'english_level': 0.05, 'hdi': 0.3, 'unemployment': 0.0, 'inflation': 0.1, 'life_expectancy': 0.4, 'distance': 0.0, 'weather': 0.4, 'known_languages': 0.0 }
}

#--- Attraction Descriptions ---
ATTRACTION_DESCRIPTIONS = {
    "Historic_Heritage": "Castles, ruins, historic sites, monuments, and museums focused on history.",
    "Religion": "Churches, cathedrals, mosques, synagogues, and other religious sites.",
    "Nature_Recreation": "Parks, gardens, beaches, mountains, hiking trails, lakes, and other natural landscapes.",
    "Culture_Art": "Art museums, galleries, architectural buildings, theaters, operas, and cultural events.",
    "Museums": "A general category for all types of museums (art, history, science, specialty).",
    "Entertainment_Leisure": "Theme parks, zoos, aquariums, casinos, nightlife, and spas.",
    "Shopping_Urban": "Malls, street markets, famous streets, squares, and distinct neighborhoods.",
    "Food_Drink": "Wineries, breweries, distilleries, and food markets.",
    "Winter_Sports": "Ski and snowboard resorts and areas.",
    "Scenic_Transport": "Scenic railways, cable cars, ferries, and bridges.",
    "Science_Technology": "Science museums, observatories, and sites of technological interest.",
    "Beach": "Specifically sandy or pebble beaches for recreation.",
    "Mountains_and_trails": "Mountain ranges, hiking trails, and related activities.",
    "Landmark": "Famous points of interest, towers, observation decks, and iconic structures.",
    "Top_200_Popular": "A collection of the top 200 most popular attractions in Europe, based on number of votes on TripAdvisor."
}


# --- Helper functions to load data from DB ---
@st.cache_data
def load_data():
    """Loads all necessary data from the database once."""
    try:
        conn = sqlite3.connect("travel_recommendation_final.db")
        df_dest = pd.read_sql_query("SELECT * FROM destinations", conn)
        df_attr = pd.read_sql_query("SELECT * FROM attractions", conn)
        conn.close()
        # Renaming 'Country_x' to 'Country' if it exists
        country_col_name = 'Country_x' if 'Country_x' in df_dest.columns else 'Country'
        df_dest.rename(columns={country_col_name: 'Country'}, inplace=True, errors='ignore')
        return df_dest, df_attr
    except Exception as e:
        st.error(f"FATAL ERROR: Could not load data from the database. Please ensure 'travel_recommendation_final.db' exists. Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data
def get_language_list(data):
    """Loads a unique, sorted list of languages from the dataframe."""
    if 'Language' in data.columns:
        return sorted([lang for lang in data['Language'].unique() if pd.notna(lang) and lang])
    return ['SOMETHING WENT WRONG']

@st.cache_data
def get_countries_and_destinations(data):
    #COUNTRIES AND DESTINATIONS
    if 'Destination' in data.columns and 'Country' in data.columns:
        df = data[['Destination', 'Country']].dropna().drop_duplicates()
        df['formatted_destination'] = df['Country'] + " - " + df['Destination']
        destinations = sorted(df['formatted_destination'].unique())
        countries = sorted(df['Country'].unique())
        return countries, destinations
    return ['STH WENT WRONG', 'STH WENT WRONG'], ['STH WENT WRONG', 'STH WENT WRONG']

# --- Chatbot Logic ---
def find_entity_in_question(question, entity_list):
    """Finds a known entity (destination or country) in the user's question."""
    question_lower = question.lower()
    for entity in sorted(entity_list, key=len, reverse=True):
        if entity.lower() in question_lower:
            return entity
    return None

def get_chatbot_response(question, dest_data, attr_data, all_destinations, all_countries, all_months):
    """The main chatbot logic function."""
    question_lower = question.lower().strip()
    raw_destinations = [d.split(' - ')[-1] for d in all_destinations]
    destination = find_entity_in_question(question, raw_destinations)
    country = find_entity_in_question(question, all_countries) if not destination else None
    
    if any(word in question_lower for word in ["hello", "hi", "hey"]):
        return """
    ### Welcome to the Personal Travel Recommender!

    Here's a quick guide on how to use the application:

    **1. Choose Your Goal in the Sidebar**
    * **Vacation:** For planning short-term trips. This mode focuses on factors like budget, attractions, and weather for a specific month.
    * **Emigration:** For evaluating long-term living prospects. This mode uses year-round climate data and focuses on socio-economic factors like cost of living, safety, and purchasing power.

    **2. Define Your Preferences**
    * Use the widgets in the sidebar to tell the model what you're looking for. The options will change depending on the goal you've selected.

    **3. Fine-Tune the Model (Optional)**
    * In the "Adjust Model Weights" section, you can load a preset "persona" (like 'Budget Explorer' or 'The Family') to automatically set the importance of each factor. You can then fine-tune any of the sliders yourself.

    **4. Get Recommendations**
    * Once you're ready, click the "Find..." button to generate your personalized list of the top 10 destinations.

    **5. Ask Me Anything!**
    * You can also use me, the chatbot, to ask specific questions like "What is the safety in Berlin?", "Tell me about Rome", or "Show me flights to Paris".

    **Ready to start? Select your goal in the sidebar!**
    """


    #Help command
    if "help" in question_lower:
        return """
        I can help you with a few things. Try asking:
        - **Find data**: "What is the HDI for Germany?" or "Weather in Rome in May?". I can find data for any metric used in the model.
        - **Explain concepts**: "How do weights work?", "How does the model work?", or "What is HDI?".
        - **Find top attractions**: "What is the most popular attraction in London?".
        - **Get a summary**: "Tell me about Warsaw".
        - **Find deals & info**: "Show me flights to Paris" or "Find hotels in Barcelona".
        """
    
    # First, check for an entity (destination or country)
    entity = destination if destination else country
    if entity:
        if destination: entity_data = dest_data[dest_data['Destination'] == entity]
        else: entity_data = dest_data[dest_data['Country'] == entity]
        if entity_data.empty: return f"Sorry, I couldn't find any data for {entity}."

        # Most popular attraction
        if "most popular" in question_lower and "attraction" in question_lower:
            if destination and not attr_data.empty:
                top_attraction = attr_data[attr_data['Destination'] == destination].sort_values(by='No_votes', ascending=False).iloc[0]
                name = top_attraction['Name']
                url = f"https://www.google.com/search?q={name.replace(' ', '+')}"
                return f"The most popular attraction in **{destination}** (based on number of votes) is **{name}**.\n\n[Search for more info here]({url})"
            else:
                return "Sorry, I can only find the most popular attraction for a specific destination, not an entire country."
        
        # Tell me about
        if "tell me about" in question_lower:
            data_row = entity_data.iloc[0]
            info = f"### Summary for **{entity}**:\n"
            info += f"- **Safety Index:** {data_row.get('Safety_Index', 'N/A')}\n"
            info += f"- **Cost of Living + Rent Index:** {data_row.get('CostofLivingPlusRentIndex', 'N/A')}\n"
            info += f"- **Purchasing Power Index:** {data_row.get('LocalPurchasingPowerIndex', 'N/A')}\n"
            info += f"- **Cuisine Rank:** {data_row.get('Cuisine_Rank', 'N/A')}\n"
            url = f"https://en.wikipedia.org/wiki/{entity.replace(' ', '_')}"
            info += f"\n[Read more on Wikipedia]({url})"
            return info

        # Data lookup from the database
        data_keywords = {"hdi": ("HDI_Value_Latest", ".3f"),"safety": ("Safety_Index", ".2f"),"cost of living": ("CostofLivingPlusRentIndex", ".2f"),"purchasing power": ("LocalPurchasingPowerIndex", ".2f"),"unemployment": ("Unemployment_Rate_National_Latest_Pct", ".2f"),"inflation": ("Inflation_Rate_National_Latest_Pct", ".2f"),"life expectancy": ("Life_Expectancy", ".2f"),"cuisine rank": ("Cuisine_Rank", ".0f")}
        for keyword, (col, fmt) in data_keywords.items():
            if keyword in question_lower and col in entity_data.columns:
                value = pd.to_numeric(entity_data[col], errors='coerce').mean()
                return f"The average {keyword.replace('_', ' ')} for **{entity}** is: **{value:{fmt}}**."
        if "weather" in question_lower:
            for month in all_months:
                if month.lower() in question_lower:
                    month_abbr = month[:3].capitalize()
                    if month_abbr in entity_data.columns:
                        weather = entity_data[month_abbr].iloc[0]
                        return f"The weather in **{entity}** in {month} is typically **{weather}**."
            return "Please specify a month to get the weather forecast (e.g., 'weather in Paris in July')."
        
        # Link generation

        if "flight" in question_lower:
            url = f"https://www.google.com/flights?q=flights+from+Poland+to+{entity.replace(' ', '+')}"
            return f"Sure, here is a link to search for flights to {entity}:\n[Click here for flights]({url})"
        if "hotel" in question_lower:
            url = f"https://www.booking.com/searchresults.html?ss={entity.replace(' ', '+')}"
            return f"Of course, here is a link to search for hotels in {entity}:\n[Click here for hotels]({url})"
        if "wikipedia" in question_lower or "information" in question_lower:
            url = f"https://en.wikipedia.org/wiki/{entity.replace(' ', '_')}"
            return f"Here is the Wikipedia page for {entity}:\n[Read more on Wikipedia]({url})"
            
    # Rule 3: Explanations (checked only if no entity was found)
    if "weights" in question_lower:
        return "A higher weight gives a factor more influence on the final recommendation score, allowing you to match the results to what's most important to you."
    if "model" in question_lower:
        return "The model uses a Weighted Scoring System. For each destination, it calculates a score (from 0 to 1) for various factors like weather, budget, and safety. Each score is then multiplied by its user-defined weight. The final score is the sum of all these weighted scores, and the top 10 destinations are recommended."
    if "hdi" in question_lower:
        return "The Human Development Index (HDI) is a statistical composite index of life expectancy, education, and per capita income indicators, which is used to rank countries into four tiers of human development. It provides a broader measure of development than just economic factors, reflecting the overall quality of life in a country."
    if "safety" in question_lower:
        return "Safety Index is a measure of how safe a country or city is for residents and visitors. It takes into account factors like crime rates, political stability, healthcare quality, and emergency services. A higher Safety Index indicates a safer environment."
    if "cost of living" in question_lower:
        return "Cost of Living Index measures the relative cost of living in different locations. It includes expenses like housing, food, transportation, healthcare, and entertainment. A lower index means that living in that location is generally more affordable."
    if "purchasing power" in question_lower:
        return "Purchasing Power Index indicates how much a local currency can buy in terms of goods and services. It reflects the relative value of money in a specific location, showing how far a salary can go in that area. A higher index means that your money has more purchasing power."
    if "cuisine rank" in question_lower:
        return "Cuisine Rank is a measure of the quality and diversity of a destination's food scene. It considers factors like the variety of cuisines available, the number of high-rated restaurants, and the overall culinary experience. A higher rank indicates a more vibrant and appealing food culture."   
    if "weather" in question_lower:
        return "In this model, weather is categorized into five types: cold, cool, mild, warm, and hot. Each destination is rated based on its typical weather conditions during different months of the year. This helps match your preferred climate with destinations that are likely to offer that experience."
    if "attraction" in question_lower or "what are attractions" in question_lower:
        return "Attractions refer to points of interest that draw visitors to a destination. They can include natural sites like parks and beaches, cultural landmarks like museums and historic sites, entertainment venues like theme parks and theaters, and many other types of places that offer unique experiences."
    if "distance" in question_lower:
        return "Distance in this model refers to the road distance from Lodz, Poland to the destination. It is used as a factor to prefer closer destinations, which can be more convenient and cost-effective to travel to."
    if "known languages" in question_lower:
        return "Known Languages refers to the languages that you, the user, can speak. If you know the local language of a destination, it gives that destination a significant bonus in its recommendation score, as it can enhance your experience and ease of communication while traveling."    
    if "attraction quantity" in question_lower:
        return "Attraction Quantity measures the number of attractions in a destination that match your interests. A higher quantity indicates that there are more options for things to see and do that align with what you enjoy."    
    if "attraction quality" in question_lower:
        return "Attraction Quality assesses how highly-rated the attractions in a destination are, based on user reviews and ratings. A higher quality score means that the attractions you are interested in are generally well-regarded and likely to provide a better experience."
    if "attraction popularity" in question_lower:
        return "Attraction Popularity indicates how well-known and frequently visited the attractions in a destination are. A higher popularity score means that the destination has famous landmarks and sites that attract many tourists, while a lower score may indicate hidden gems and less crowded places."
    if "cuisine quality" in question_lower:
        return "Cuisine Quality evaluates the overall quality of the food scene in a destination, based on factors like restaurant ratings, diversity of culinary options, and local food culture. A higher cuisine quality score suggests that the destination offers a rich and satisfying dining experience."
 
    #Default response
    return "Sorry, I don't understand that question. Try asking 'help' to see what I can do."

def display_recommendations(recommendations_df, all_data_df):
    #DISPLAYING RECOMMENDATIONS
    if recommendations_df is not None and not recommendations_df.empty:
        col1, col2 = st.columns([4, 3])
        #LEFT: TABLE, RIGHT: MAP
        with col1:
            st.subheader("Top 10 Recommendations")
            recs_to_display = recommendations_df.copy()
            if 'Country_x' in recs_to_display.columns:
                recs_to_display.rename(columns={'Country_x': 'Country'}, inplace=True)
            recs_to_display.insert(0, 'Rank', range(1, 1 + len(recs_to_display)))
            def highlight_top3(row):
                if row.Rank <= 3:
                    return ['background-color: #d4edda'] * len(row)
                return [''] * len(row)
            st.dataframe(recs_to_display.style.apply(highlight_top3, axis=1), hide_index=True)
        with col2:
            st.subheader("Map of Recommendations")
            lat_col = next((col for col in all_data_df.columns if 'latitude' in col.lower()), None)
            lon_col = next((col for col in all_data_df.columns if 'longitude' in col.lower()), None)
            if lat_col and lon_col:
                map_data = pd.merge(recs_to_display, all_data_df[['Destination', lat_col, lon_col]], on='Destination', how='left')
                map_data[lat_col] = pd.to_numeric(map_data[lat_col], errors='coerce')
                map_data[lon_col] = pd.to_numeric(map_data[lon_col], errors='coerce')
                map_data.dropna(subset=[lat_col, lon_col], inplace=True)
                if not map_data.empty:
                    m = folium.Map(location=[map_data[lat_col].mean(), map_data[lon_col].mean()], zoom_start=4)
                    for idx, row in map_data.iterrows():
                        icon_html = f'''<div style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 14px; font-weight: bold; color: white; background-color: #007BFF; border: 2px solid white; border-radius: 50%; width: 28px; height: 28px; text-align: center; line-height: 24px; box-shadow: 2px 2px 4px rgba(0,0,0,0.5);">{row['Rank']}</div>'''
                        folium.Marker(
                            location=[row[lat_col], row[lon_col]],
                            popup=f"#{row['Rank']}: {row['Destination']}",
                            tooltip=f"#{row['Rank']}: {row['Destination']}",
                            icon=folium.DivIcon(html=icon_html)
                        ).add_to(m)
                    st_folium(m, width=700, height=450)
                else:
                    st.warning("Could not display map - coordinate data is missing for recommendations.")
            else:
                st.warning("Could not find latitude/longitude columns in the database to display the map.")
    else:
        st.error("No recommendations found for the given criteria.")


# --- Main App ---
st.title('Personal Travel Recommender')
main_df, attr_df = load_data()
#CHATBOT INTERFACE
st.sidebar.title("Ask the Travel Bot!")
if not main_df.empty:
    st.sidebar.title('Define your preferences!')
    language_options = get_language_list(main_df)
    country_options, destination_options = get_countries_and_destinations(main_df)
    month_options = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    mode = st.sidebar.radio("Choose your goal:", ('Vacation', 'Emigration'))
    st.sidebar.subheader("Exclude Places", help="You can exclude entire countries or specific destinations from the recommendations.")
    excluded_countries = st.sidebar.multiselect('STEP 1: Exclude entire countries:', options=country_options)
    excluded_destinations_formatted = st.sidebar.multiselect('STEP 2: Exclude specific destinations:', options=destination_options)
    excluded_destinations = [d.split(' - ')[-1] for d in excluded_destinations_formatted]
    final_excluded_list = excluded_countries + excluded_destinations
    if mode == 'Vacation':
        st.header("Vacation Recommendations")
        with st.sidebar:
            st.subheader("Main Preferences", help="These are the main criteria that will influence the recommendations.")
            month_pref = st.selectbox('STEP 3: Select month of travel:', options=month_options, index=6, help="The model will search for destinations with the best weather in your chosen month.")
            weather_pref = st.selectbox('STEP 4: Select your dream weather:', options=WEATHER_SCALE, index=5, help="Select your ideal weather. Destinations with similar weather will get more points.")            
            help_text_lines = ["**'everything'**: Considers all attractions, prioritizing destinations with the highest quantity and quality of attractions overall.\n\n**Category Descriptions:**\n"]
            for group, description in ATTRACTION_DESCRIPTIONS.items():
                help_text_lines.append(f"- **{group.replace('_', ' ')}:** {description}")
            attraction_help_text = "\n".join(help_text_lines)

            attraction_pref = st.multiselect(
                'STEP 5: What types of attractions are you interested in?', 
                options=['everything'] + ALL_ATTRACTION_GROUPS, 
                default=['everything'],
                help=attraction_help_text
            )
            
            known_languages_pref = st.multiselect('STEP 6: What other languages do you speak?', options=language_options, help="If you know the local language, the destination will receive a significant bonus in its score.")
            
            with st.expander("STEP 7: ADJUST MODEL WEIGHTS", expanded=True):
                persona = st.selectbox("Load a preset...", options=list(VACATION_PRESETS.keys()), key='vac_persona')
                weights = VACATION_PRESETS[persona]
                w_weather = st.slider("Weight: Weather", 0.0, 1.0, weights['weather'], 0.05, key='w_vac_weather', help="Controls the importance of the weather matching your preference.")
                w_budget = st.slider("Weight: Budget", 0.0, 1.0, weights['budget'], 0.05, key='w_vac_budget', help="Controls the importance of the daily vacation cost matching your budget.")
                w_attr_quantity = st.slider("Weight: Attraction Quantity", 0.0, 1.0, weights['attractions_quantity'], 0.05, key='w_vac_attr_qnt', help="Controls the importance of having a large number of attractions that match your interests.")
                w_attr_quality = st.slider("Weight: Attraction Quality", 0.0, 1.0, weights['attractions_quality'], 0.05, key='w_vac_attr_ql', help="Controls the importance of how highly-rated the attractions of interest are.")
                w_safety = st.slider("Weight: Safety", 0.0, 1.0, weights['safety'], 0.05, key='w_vac_safety', help="Controls the importance of the destination's safety index.")
                w_attr_pop = st.slider('Weight: Popularity', -1.0, 1.0, weights['attractions_popularity'], 0.05, key='w_vac_attr_pop', help="Positive values prefer famous destinations. Negative values prefer less crowded, hidden gems.")
                w_eng_level = st.slider("Weight: English Level", 0.0, 1.0, weights['english_level'], 0.05, key='w_vac_eng', help="Controls the importance of high English proficiency in the destination.")
                w_known_lang = st.slider("Weight: Known Languages", 0.0, 1.0, weights['known_languages'], 0.05, key='w_vac_lang', help="Controls the bonus for destinations where you speak the local language.")
                w_distance = st.slider("Weight: Distance", 0.0, 1.0, weights['distance'], 0.05, key='w_vac_dist', help="Controls the importance of the road distance from Lodz, Poland (closer is better).")
                w_cuisine = st.slider("Weight: Cuisine Quality", 0.0, 1.0, weights['cuisine_quality'], 0.05, key='w_vac_cuisine', help="Controls the importance of the destination's international cuisine ranking.")

        if 'vacation_recs' not in st.session_state:
            st.session_state.vacation_recs = None
        if st.button('Find my perfect vacation!'):
            if not attraction_pref: st.sidebar.error("Please select at least one attraction type (or 'everything').")
            else:
                vacation_preferences = {'month': month_pref,'weather': weather_pref,'attractions': attraction_pref,'known_languages': known_languages_pref,'excluded_places': final_excluded_list}
                vacation_weights = {'weather': w_weather, 'budget': w_budget, 'attractions_quantity': w_attr_quantity, 'attractions_quality': w_attr_quality, 'safety': w_safety, 'attractions_popularity': w_attr_pop, 'english_level': w_eng_level, 'known_languages': w_known_lang, 'distance': w_distance, 'cuisine_quality': w_cuisine}
                with st.spinner('Thinking...'):
                    recommendations = get_vacation_recommendations(vacation_preferences, vacation_weights)
                    st.session_state.vacation_recs = recommendations
                st.success('Done!')
        if st.session_state.vacation_recs is not None:
            display_recommendations(st.session_state.vacation_recs, main_df)

    elif mode == 'Emigration':
        st.header("Emigration Recommendations")
        with st.sidebar:
            st.subheader("Main Preferences", help="These are the main criteria that will influence the recommendations for long-term living.")
            weather_pref_em = st.selectbox('STEP 3: What temperature do you prefer year-round?', options=WEATHER_SCALE, index=4, key='weather_em', help="The model rewards destinations that match this climate for the majority of the year.")
            known_languages_pref_em = st.multiselect('STEP 4: What other languages do you speak?', options=language_options, key='lang_em', help="If you know the local language, the destination will receive a significant bonus in its score.")
            with st.expander("STEP 5: Adjust Model Weights"):
                persona_em = st.selectbox("Load a preset...", options=list(EMIGRATION_PRESETS.keys()), key='em_persona')
                weights_em = EMIGRATION_PRESETS[persona_em]
                w_cost_living = st.slider("Weight: Cost of Living", 0.0, 1.0, weights_em['cost_of_living'], 0.05, key='w_em_cost', help="Importance of low cost of living, including rent.")
                w_purchasing_power = st.slider("Weight: Purchasing Power", 0.0, 1.0, weights_em['purchasing_power'], 0.05, key='w_em_power', help="Importance of high local purchasing power (what you can buy on a local salary).")
                w_safety_em = st.slider("Weight: Safety", 0.0, 1.0, weights_em['safety'], 0.05, key='w_em_safety', help="Importance of a high safety index.")
                w_eng_level_em = st.slider("Weight: English Level", 0.0, 1.0, weights_em['english_level'], 0.05, key='w_em_eng', help="Importance of high English proficiency in the destination.")
                w_hdi = st.slider("Weight: HDI", 0.0, 1.0, weights_em['hdi'], 0.05, key='w_em_hdi', help="Importance of the Human Development Index (overall quality of life).")
                w_unemployment = st.slider("Weight: Unemployment", 0.0, 1.0, weights_em['unemployment'], 0.05, key='w_em_unemp', help="Importance of a low unemployment rate.")
                w_inflation = st.slider("Weight: Inflation", 0.0, 1.0, weights_em['inflation'], 0.05, key='w_em_infl', help="Importance of a low and stable inflation rate.")
                w_life_exp = st.slider("Weight: Life Expectancy", 0.0, 1.0, weights_em['life_expectancy'], 0.05, key='w_em_life', help="Importance of high life expectancy as an indicator of healthcare and quality of life.")
                w_distance_em = st.slider("Weight: Distance", 0.0, 1.0, weights_em['distance'], 0.05, key='w_em_dist', help="Importance of the road distance from Lodz, Poland (closer is better).")
                w_weather_em = st.slider("Weight: Weather", 0.0, 1.0, weights_em['weather'], 0.05, key='w_em_weather', help="Importance of a pleasant year-round climate.")
                w_known_lang_em = st.slider("Weight: Known Languages", 0.0, 1.0, weights_em['known_languages'], 0.05, key='w_em_lang', help="Controls the bonus for destinations where you speak the local language.")
        
        if 'emigration_recs' not in st.session_state:
            st.session_state.emigration_recs = None
        if st.button('Find the best place to live!'):
            emigration_preferences = {'weather': weather_pref_em, 'known_languages': known_languages_pref_em,'excluded_places': final_excluded_list}
            emigration_weights = {'cost_of_living': w_cost_living, 'purchasing_power': w_purchasing_power, 'safety': w_safety_em, 'english_level': w_eng_level_em, 'hdi': w_hdi, 'unemployment': w_unemployment, 'inflation': w_inflation, 'life_expectancy': w_life_exp, 'distance': w_distance_em,'weather': w_weather_em, 'known_languages': w_known_lang_em}
            with st.spinner('Thinking...'):
                recommendations = get_emigration_recommendations(emigration_preferences, emigration_weights)
                st.session_state.emigration_recs = recommendations
            st.success('Done!')
        
        if st.session_state.emigration_recs is not None:
            display_recommendations(st.session_state.emigration_recs, main_df)

    # --- Chatbot Interface ---
    st.markdown("---")
    st.header("Travel Assistant Chatbot")
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": """
    ### Welcome to the Personal Travel Recommender!

    Here's a quick guide on how to use the application:

    **FIRST STEP. Choose Your Goal in the Sidebar**
    * **Vacation:** For planning short-term trips. This mode focuses on factors like budget, attractions, and weather for a specific month.
    * **Emigration:** For evaluating long-term living prospects. This mode uses year-round climate data and focuses on socio-economic factors like cost of living, safety, and purchasing power.

    **NEXT STEPS. Define Your Preferences**
    * Use the widgets in the sidebar to tell the model what you're looking for. The options will change depending on the goal you've selected.

    **LAST STEP. Fine-Tune the Model**
    * In the "Adjust Model Weights" section, you can load a preset "persona" (like 'Budget Explorer' or 'The Family') to automatically set the importance of each factor. You can then fine-tune any of the sliders yourself.

    **Get your Recommendations**
    * Once you're ready, click the "Find..." button to generate your personalized list of the top 10 destinations.

    **Ask Me Anything!**
    * You can also use me, the chatbot, to ask specific questions like "What is the safety in Berlin?", "Tell me about Rome", or "Show me flights to Paris".

    **Ready to start? Select your goal in the sidebar!**
    """}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about flights, hotels, safety..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.spinner("Thinking..."):
            raw_destination_names = [d.split(' - ')[-1] for d in destination_options]
            response = get_chatbot_response(prompt, main_df, attr_df, raw_destination_names, country_options, month_options)
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
else:
    st.error("Could not load the database. Please make sure the 'travel_recommendation_final.db' file is in the same folder as the script.")