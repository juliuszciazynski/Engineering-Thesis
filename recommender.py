import pandas as pd
import sqlite3
import re




#SCALE FOR WEATHER PREFERENCE  
WEATHER_SCALE = ['freezing', 'very cold', 'cold', 'cool', 'comfortable', 'warm', 'hot', 'sweltering'] 
#ATTRACTION GROUPS
ALL_ATTRACTION_GROUPS = [
    'Historic_Heritage', 'Religion', 'Nature_Recreation', 'Culture_Art', 'Museums',
    'Entertainment_Leisure', 'Shopping_Urban', 'Food_Drink', 'Winter_Sports',
    'Scenic_Transport', 'Science_Technology', 'Beach', 'Mountains_and_trails',
    'Landmark', 'Top_200_Popular'
]

#POPULARITY SCORE FUNCTION
def calculate_attraction_popularity_score(rank, max_rank):
    """Non-linear function for scoring attraction popularity."""
    if pd.isna(rank): return 0.0
    if rank == 1: return 1.0
    elif rank <= 5: return 0.9
    elif rank <= 20: return 0.8
    elif rank <= 50: return 0.7
    elif rank <= 100: return 0.6
    elif rank <= 200: return 0.5
    elif rank <= 500: return 0.3
    elif rank <= 1000: return 0.2
    elif rank <= max_rank / 2: return 0.1
    else: return 0.05

#CUISINE SCORE
def calculate_cuisine_score(rank, max_rank=100):
    #IF NOT IN THE TOP 100, NO POINTS
    if pd.isna(rank) or rank <= 0 or rank > max_rank:
        return 0.0
    #CALCULATING THE CUISINE COEFFICIENT
    score = (1 - ((rank - 1) / (max_rank - 1))) ** 2
    return score


#VACATION RECOMMENDATION
def get_vacation_recommendations(preferences, weights, top_n=10):
    #CONNECTING TO TRAVEL_RECOMMENDATION DATABASE
    try:
        conn = sqlite3.connect("travel_recommendation_final.db")
        df_dest = pd.read_sql_query("SELECT * FROM destinations", conn)
        df_attr = pd.read_sql_query("SELECT * FROM attractions", conn)
        conn.close()
    except Exception as e:
        print(f"Error loading data from database: {e}")
        return None

    df_attr['attraction_popularity_rank'] = df_attr['No_votes'].rank(method='max', ascending=False)
    max_rank = df_attr['attraction_popularity_rank'].max()
    #ASSIGINNG POINTS FOR POPULARITY
    df_attr['attraction_popularity_score'] = df_attr['attraction_popularity_rank'].apply(lambda r: calculate_attraction_popularity_score(r, max_rank))
    #GROUPING BY DESTINATION
    attr_grouped = df_attr.groupby('Destination').sum()
    df = pd.merge(df_dest, attr_grouped, on='Destination', how='left')
    
    #EXCLUDING PLACES
    excluded_places = preferences.get('excluded_places', [])
    if excluded_places:
        excluded_lower = [place.lower() for place in excluded_places]
        df = df[~df['Country_x'].str.lower().isin(excluded_lower)]
        df = df[~df['Destination'].str.lower().isin(excluded_lower)]
    
    df['score'] = 0.0
    
    #COEFFICIENT POINTS
    #1. WEATHER (SHOW THE GRAPH IN EXCEL.)
    #USER CHOOSES ONE MONTH AND PREFERABLE WEATHER, AND THE WEATHER FOR THIS MONTH IS COMPARED WITH THE DATABASE
    month_col = preferences.get('month', '')[:3].capitalize()
    if month_col and month_col in df.columns and weights.get('weather', 0) > 0:
        def score_weather(current_weather):
            max_allowed_distance = 3
            weather_value = str(current_weather).strip().lower()
            user_pref_lower = preferences.get('weather', '').lower()
            try:
                user_index = WEATHER_SCALE.index(user_pref_lower)
                current_index = WEATHER_SCALE.index(weather_value)
                distance = abs(user_index - current_index)
                if distance > max_allowed_distance: return 0.0
                else: return 1.0 - (distance / max_allowed_distance)
            except ValueError: return 0.0
        weather_score = df[month_col].apply(score_weather)
        df['score'] += weights['weather'] * weather_score.fillna(0)

    #2. BUDGET: SIMPLIFIED TO USE ONLY MIDRANGE COST
    #NORMALISATION (CHEAPEST PLACE = 1, MOST EXPENSIVE = 0)
    cost_col = 'Overall_Daily_Cost_MidRange_USD' # Hardcoded to MidRange
    if cost_col in df.columns and df[cost_col].max() > 0 and weights.get('budget', 0) > 0:
        cost_normalized = (df[cost_col] - df[cost_col].min()) / (df[cost_col].max() - df[cost_col].min())
        budget_score = 1 - cost_normalized
        df['score'] += weights['budget'] * budget_score.fillna(0)

    #3,4 - ATTRACTION QUANTITY AND QUALITY
    #EVERY ATTRACTION HAS SOME CATEGORIES ASSIGNED TO THEM, AND ATTRACTION QUANTITY COUNTS HOW MANY OF THESE CATEGORIES ALL 30 OF BEST ATTRACTIONS HAVE IN THE DESTINATION
    #ALL ATTRACTIONS ALSO RECEIVE AN AVERAGE SCORE, WHICH IS THEN COMPUTED FOR ALL 30 OF THEM USING WEIGHTED AVERAGE, WITH NUMBER OF VOTES AS A WEIGHT
    user_attractions = preferences.get('attractions', [])
    #USER CAN CHOOSE EVERYTHING
    attractions_to_score = ALL_ATTRACTION_GROUPS if (user_attractions and user_attractions[0].lower() == 'everything') else user_attractions

    if attractions_to_score:
        valid_attractions = [attr for attr in attractions_to_score if attr in df.columns]
        if valid_attractions:
            if weights.get('attractions_quantity', 0) > 0:
                quantity_score = df[valid_attractions].sum(axis=1)
                if quantity_score.max() > 0:
                    quantity_score_normalized = quantity_score / quantity_score.max()
                    df['score'] += weights['attractions_quantity'] * quantity_score_normalized.fillna(0)

            if weights.get('attractions_quality', 0) > 0:
                mask = df_attr[valid_attractions].sum(axis=1) > 0
                matching_attractions = df_attr[mask]
                if not matching_attractions.empty:
                    matching_attractions.loc[:, 'rating_x_votes'] = matching_attractions['Avg_rating'] * matching_attractions['No_votes']
                    quality_grouped = matching_attractions.groupby('Destination').agg(rating_x_votes_sum=('rating_x_votes', 'sum'), no_votes_sum=('No_votes', 'sum'))
                    quality_grouped['quality_score'] = quality_grouped['rating_x_votes_sum'] / quality_grouped['no_votes_sum'].replace(0, 1)
                    df = pd.merge(df, quality_grouped[['quality_score']], on='Destination', how='left')
                    if 'quality_score' in df.columns and df['quality_score'].max() > 0:
                        quality_score_normalized = (df['quality_score'] - df['quality_score'].min()) / (df['quality_score'].max() - df['quality_score'].min())
                        df['score'] += weights['attractions_quality'] * quality_score_normalized.fillna(0)
    
    #5. DISTANCE FROM LODZ
    #CLOSEST LOCATION TO LODZ RECEIVES 100% OF POINTS (HERE, IT IS WARSAW), AND THE FURTHEST RECEIVES 0 POINTS, INCLUDING THESE, WHICH ARE ISLANDS (CAR TRAVEL)
    dist_col = 'Distance_from_Lodz_km_road'
    if dist_col in df.columns and weights.get('distance', 0) > 0:
        distance_data = df[dist_col].copy()
        nan_indices = distance_data.isna()
        max_dist = distance_data[~nan_indices].max()
        min_dist = distance_data[~nan_indices].min()
        if max_dist > min_dist:
            normalized_distance = (distance_data - min_dist) / (max_dist - min_dist)
            distance_score = (1 - normalized_distance) ** 2
        else:
            distance_score = pd.Series(0.5, index=distance_data.index)
        distance_score[nan_indices] = 0.0
        df['score'] += weights['distance'] * distance_score.fillna(0)

    df.fillna(0, inplace=True)

    #6. SAFETY INDEX NORMALISED
    if 'Safety_Index' in df.columns and weights.get('safety', 0) > 0:
        safety_normalized = (df['Safety_Index'] - df['Safety_Index'].min()) / (df['Safety_Index'].max() - df['Safety_Index'].min())
        df['score'] += weights['safety'] * safety_normalized
        
    #7. POPULARITY OF ALL ATTRACTIONS SUMMED UP, NORMALISED AND RANKED
    pop_col_name = 'attraction_popularity_score'
    if pop_col_name in df.columns and df[pop_col_name].max() > 0 and weights.get('attractions_popularity', 0) != 0:
        pop_score_normalized = (df[pop_col_name] - df[pop_col_name].min()) / (df[pop_col_name].max() - df[pop_col_name].min())
        df['score'] += weights['attractions_popularity'] * pop_score_normalized

    #8. ENGLISH LEVEL (NORMALISED AS WELL)
    epi_col = 'English_EPI_Score'
    if epi_col in df.columns and weights.get('english_level', 0) > 0:
        if df[epi_col].max() > df[epi_col].min():
            epi_normalized = (df[epi_col] - df[epi_col].min()) / (df[epi_col].max() - df[epi_col].min())
        else: epi_normalized = 0.5
        df['score'] += weights['english_level'] * epi_normalized.fillna(0)
        
    #9. ADDITIONAL POINTS IF USER WANTS TO "USE" THE LANGUAGE THEY KNOW (EXCLUDING ENGLISH)
    user_languages = preferences.get('known_languages', [])
    if 'Language' in df.columns and user_languages and weights.get('known_languages', 0) > 0:
        df['score'] += weights['known_languages'] * df['Language'].apply(lambda lang: 1.0 if str(lang).lower() in [l.lower() for l in user_languages] else 0.0)

    #10. CUSINE QUALITY RANKING 
    if 'Cuisine_Rank' in df.columns and weights.get('cuisine_quality', 0) > 0:
        cuisine_score = df['Cuisine_Rank'].apply(calculate_cuisine_score)
        df['score'] += weights['cuisine_quality'] * cuisine_score

    results = df.sort_values(by='score', ascending=False)
    display_cols = ['Destination', 'Country_x', 'score']
    
    return results[display_cols].head(top_n)

#EMIGRATION RECOMMENDATION
def get_emigration_recommendations(preferences, weights, top_n=10):
    #CONNECTING AS BEFORE
    try:
        conn = sqlite3.connect("travel_recommendation_final.db")
        df = pd.read_sql_query("SELECT * FROM destinations", conn)
        conn.close()
    except Exception as e:
        print(f"Error loading data from database: {e}")
        return None

    excluded_places = preferences.get('excluded_places', [])
    if excluded_places:
        excluded_lower = [place.lower() for place in excluded_places]
        df = df[~df['Country'].str.lower().isin(excluded_lower)]
        df = df[~df['Destination'].str.lower().isin(excluded_lower)]
        
    df['score'] = 0.0
    
    #1. WEATHER, BUT HERE, POINTS ARE SUMMED FOR THE WHOLE YEAR
    if weights.get('weather', 0) > 0 and 'weather' in preferences:
        month_cols = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        df['total_weather_score'] = 0.0
        def score_weather(current_weather):
            max_allowed_distance = 3
            weather_value = str(current_weather).strip().lower()
            user_pref_lower = preferences['weather'].lower()
            try:
                user_index = WEATHER_SCALE.index(user_pref_lower)
                current_index = WEATHER_SCALE.index(weather_value)
                distance = abs(user_index - current_index)
                if distance > max_allowed_distance: return 0.0
                else: return 1.0 - (distance / max_allowed_distance)
            except ValueError: return 0.0
        for month_col in month_cols:
            if month_col in df.columns:
                monthly_score = df[month_col].apply(score_weather)
                df['total_weather_score'] += monthly_score.fillna(0)
        if df['total_weather_score'].max() > 0:
            weather_score_normalized = (df['total_weather_score'] - df['total_weather_score'].min()) / (df['total_weather_score'].max() - df['total_weather_score'].min())
            df['score'] += weights['weather'] * weather_score_normalized
        
    #2.Distance from Lodz (SAME AS IN TOURISM)
    dist_col = 'Distance_from_Lodz_km_road'
    if dist_col in df.columns and weights.get('distance', 0) > 0:
        distance_data = df[dist_col].copy()
        nan_indices = distance_data.isna()
        max_dist = distance_data[~nan_indices].max()
        min_dist = distance_data[~nan_indices].min()
        if max_dist > min_dist:
            normalized_distance = (distance_data - min_dist) / (max_dist - min_dist)
            distance_score = (1 - normalized_distance) ** 2
        else:
            distance_score = pd.Series(0.5, index=distance_data.index)
        distance_score[nan_indices] = 0.0
        df['score'] += weights['distance'] * distance_score.fillna(0)

    df.fillna(0, inplace=True)
    
    #3,4,5. COST OF LIVING INDEX, UNEMPLOYMENT, INFLATION, THE LOWER THE BETTER, NORMALISED
    for col, weight in [('CostofLivingPlusRentIndex', 'cost_of_living'), ('Unemployment_Rate_National_Latest_Pct', 'unemployment'), ('Inflation_Rate_National_Latest_Pct', 'inflation')]:
        if col in df.columns and weights.get(weight, 0) > 0:
            if df[col].max() > df[col].min():
                normalized = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
                df['score'] += weights[weight] * (1 - normalized)

    #6,7,8,9 PURCHASING POWER, SAFETY INDEX, HDI, LIFE EXPECTANCY, THE HIGHER THE BETTER
    for col, weight in [('LocalPurchasingPowerIndex', 'purchasing_power'), ('Safety_Index', 'safety'), ('HDI_Value_Latest', 'hdi'), ('Life_Expectancy', 'life_expectancy')]:
        if col in df.columns and weights.get(weight, 0) > 0:
            if df[col].max() > df[col].min():
                normalized = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
                df['score'] += weights[weight] * normalized

    #10. ENGLISH (SAME AS BEFORE)
    epi_col = 'English_EPI_Score'
    if epi_col in df.columns and weights.get('english_level', 0) > 0:
        if df[epi_col].max() > df[epi_col].min():
            epi_normalized = (df[epi_col] - df[epi_col].min()) / (df[epi_col].max() - df[epi_col].min())
        else: epi_normalized = 0.5
        df['score'] += weights['english_level'] * epi_normalized.fillna(0)
    #ADDITIONAL LANGUAGES (SAME AS BEFORE)   
    user_languages = preferences.get('known_languages', [])
    if 'Language' in df.columns and user_languages and weights.get('known_languages', 0) > 0:
        df['score'] += weights['known_languages'] * df['Language'].apply(lambda lang: 1.0 if str(lang).lower() in [l.lower() for l in user_languages] else 0.0)

    results = df.sort_values(by='score', ascending=False)
    display_cols = ['Destination', 'Country', 'score']
    
    return results[display_cols].head(top_n)

#MAIN PROGRAM
if __name__ == "__main__":
    #USER CHOOSES MODE
    choice = input("Choose recommendation mode ('vacation' or 'emigration'): ").lower().strip()

    if choice == 'vacation':
        print("\n" + "="*50); print(" RUNNING VACATION MODE ".center(50, "=")); print("="*50)
        #USER CHOSES MONTH, PREFERRED WEATHER, HIS "BUDGET RANGE", ATTRACTIONS THEY ARE INTERESTED IN, KNOWN LANGUAGES, AND CAN EXCLUDE COUNTRIES OR DESTINATIONS
        vacation_preferences = {
            'month': 'July',
            'weather': 'warm',
            'attractions': ['Top_200_Popular'],
            'known_languages': [],
            'excluded_places': ['Poland']
        }
        #USER ASSIGNS WEIGHTS TO ALL CATEGORIES
        vacation_weights = {
            'weather': 0, 'budget': 1, 'attractions_quantity': 0, 'attractions_quality': 0,
            'safety': 0, 'attractions_popularity': 0, 'english_level': 0, 'known_languages': 0.0,
            'distance': 0, 'cuisine_quality': 0
        }
        
        recommendations = get_vacation_recommendations(vacation_preferences, vacation_weights)
        if recommendations is not None:
            print("\n--- Top 10 Vacation Recommendations ---")
            recommendations.rename(columns={'Country_x': 'Country'}, inplace=True)
            print(recommendations.to_string(index=False))
    #USER CAN CHOOSE EMIGRATION MODE
    elif choice == 'emigration':
        print("\n" + "="*50); print(" RUNNING EMIGRATION MODE ".center(50, "=")); print("="*50)
        #USER CAN EXCLUDE COUNTRIES OR DESTINATIONS, LIST KNOWN LANGUAGES, AND PREFERRED WEATHER
        emigration_preferences = {
            'excluded_places': [],
            'known_languages': [],
            'weather': 'comfortable'
        }
        #USER ASSIGNS WEIGHTS TO ALL CATEGORIES
        emigration_weights = {
            'cost_of_living': 0.20, 'purchasing_power': 0.20, 'safety': 0.10,
            'english_level': 0.10, 'hdi': 0.10, 'unemployment': 0.10,
            'known_languages': 0.0, 'inflation': 0.10, 'life_expectancy': 0.05,
            'distance': 0.0, 'weather': 0.05
        }
        
        recommendations = get_emigration_recommendations(emigration_preferences, emigration_weights)
        if recommendations is not None:
            print("\n--- Top 10 Emigration Recommendations ---")
            print(recommendations.to_string(index=False))
            
    else:
        print("\nInvalid choice. Please enter 'vacation' or 'emigration'.")
