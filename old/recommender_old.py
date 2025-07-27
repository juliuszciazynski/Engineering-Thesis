import pandas as pd
import sqlite3
import re

# --- Stałe i funkcje pomocnicze ---

WEATHER_SCALE = ['freezing', 'very cold', 'cold', 'cool', 'comfortable', 'warm', 'hot', 'sweltering']
ALL_ATTRACTION_GROUPS = [
    'Historic_Heritage', 'Religion', 'Nature_Recreation', 'Culture_Art', 'Museums',
    'Entertainment_Leisure', 'Shopping_Urban', 'Food_Drink', 'Winter_Sports',
    'Scenic_Transport', 'Science_Technology', 'Beach', 'Mountains_and_trails',
    'Landmark'
]

def calculate_attraction_popularity_score(rank, max_rank):
    """Nieliniowa funkcja do oceny popularności atrakcji."""
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

def calculate_cuisine_score(rank, max_rank=100):
    """Nieliniowa, 'agresywna' funkcja do oceny jakości kuchni."""
    if pd.isna(rank) or rank >= max_rank:
        return 0.0
    score = (1 - (rank / max_rank)) ** 2
    return score

# --- Główna funkcja rekomendacyjna ---

def get_recommendations(preferences, weights, top_n=10):
    """
    Główna funkcja modelu rekomendacyjnego.
    """
    try:
        conn = sqlite3.connect("travel_recommendation_final.db")
        df_dest = pd.read_sql_query("SELECT * FROM destinations", conn)
        df_attr = pd.read_sql_query("SELECT * FROM attractions", conn)
        conn.close()
    except Exception as e:
        print(f"Błąd podczas wczytywania danych z bazy: {e}")
        return None

    # --- Przygotowanie Danych ---
    # Obliczenie rankingu i wyniku popularności dla każdej atrakcji
    df_attr['attraction_popularity_rank'] = df_attr['No_votes'].rank(method='max', ascending=False)
    max_rank = df_attr['attraction_popularity_rank'].max()
    df_attr['attraction_popularity_score'] = df_attr['attraction_popularity_rank'].apply(lambda r: calculate_attraction_popularity_score(r, max_rank))
    
    # Agregacja danych o ilości atrakcji i ich ogólnej popularności
    attr_grouped = df_attr.groupby('Destination').sum()
    
    # Połączenie w jeden główny DataFrame
    df = pd.merge(df_dest, attr_grouped, on='Destination', how='left')
    
    # Filtr wykluczonych miejsc
    excluded_places = preferences.get('excluded_places', [])
    if excluded_places:
        excluded_lower = [place.lower() for place in excluded_places]
        df = df[~df['Country_x'].str.lower().isin(excluded_lower)]
        df = df[~df['Destination'].str.lower().isin(excluded_lower)]
    
    # Inicjalizacja kolumny z wynikiem
    df['score'] = 0.0
    
    # --- System Punktacji Ważonej ---

    # 1. Pogoda
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

    # 2. Budżet (dla trybu "Wakacje")
    cost_col_map = {'Budget': 'Overall_Daily_Cost_Budget_USD', 'MidRange': 'Overall_Daily_Cost_MidRange_USD', 'Luxury': 'Overall_Daily_Cost_Luxury_USD'}
    cost_col = cost_col_map.get(preferences.get('budget'))
    if cost_col and cost_col in df.columns and df[cost_col].max() > 0 and weights.get('budget', 0) > 0:
        cost_normalized = (df[cost_col] - df[cost_col].min()) / (df[cost_col].max() - df[cost_col].min())
        budget_score = 1 - cost_normalized
        df['score'] += weights['budget'] * budget_score.fillna(0)

    # 3a & 3b. Ilość i Jakość Atrakcji (spersonalizowane)
    user_attractions = preferences.get('attractions', [])
    attractions_to_score = ALL_ATTRACTION_GROUPS if (user_attractions and user_attractions[0].lower() == 'everything') else user_attractions
    
    if attractions_to_score:
        valid_attractions = [attr for attr in attractions_to_score if attr in df.columns]
        if valid_attractions:
            # 3a. Ilość
            if weights.get('attractions_quantity', 0) > 0:
                quantity_score = df[valid_attractions].sum(axis=1)
                if quantity_score.max() > 0:
                    quantity_score_normalized = quantity_score / quantity_score.max()
                    df['score'] += weights['attractions_quantity'] * quantity_score_normalized.fillna(0)

            # 3b. Jakość (średnia ważona)
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

    # 8. Odległość od Łodzi
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

    # Uzupełniamy wszystkie pozostałe NaN zerami DOPIERO po wszystkich obliczeniach wrażliwych na NaN
    df.fillna(0, inplace=True)

    # 4. Bezpieczeństwo
    if 'Safety_Index' in df.columns and weights.get('safety', 0) > 0:
        df['score'] += weights['safety'] * (df['Safety_Index'] / 100)
        
    # 5. Popularność Atrakcji (niespersonalizowana, z wagą ujemną)
    pop_col_name = 'attraction_popularity_score'
    if pop_col_name in df.columns and df[pop_col_name].max() > 0 and weights.get('attractions_popularity', 0) != 0:
        pop_score_normalized = (df[pop_col_name] - df[pop_col_name].min()) / (df[pop_col_name].max() - df[pop_col_name].min())
        df['score'] += weights['attractions_popularity'] * pop_score_normalized

    # 6. Poziom języka angielskiego
    if 'English_level' in df.columns and weights.get('english_level', 0) > 0:
        score_map = {'very high': 1.0, 'high': 0.8, 'moderate': 0.5, 'low': 0.2, 'Unknown': 0.0}
        df['score'] += weights['english_level'] * df['English_level'].str.lower().map(score_map).fillna(0)
        
    # 7. Znajomość języków lokalnych
    user_languages = preferences.get('known_languages', [])
    if 'Language' in df.columns and user_languages and weights.get('known_languages', 0) > 0:
        df['score'] += weights['known_languages'] * df['Language'].apply(lambda lang: 1.0 if str(lang).lower() in [l.lower() for l in user_languages] else 0.0)

    # 9. Jakość kuchni
    if 'Cuisine_Rank' in df.columns and weights.get('cuisine_quality', 0) > 0:
        cuisine_score = df['Cuisine_Rank'].apply(calculate_cuisine_score)
        df['score'] += weights['cuisine_quality'] * cuisine_score

    # --- Zwrócenie wyników ---
    results = df.sort_values(by='score', ascending=False)
    display_cols = ['Destination', 'Country_x', 'score']
    
    return results[display_cols].head(top_n)

# --- PRZYKŁAD UŻYCIA MODELU ---
if __name__ == "__main__":
    
    user_preferences = {
        'month': 'September',
        'weather': 'comfortable',
        'budget': 'MidRange',
        'attractions': ['Historic_Heritage', 'Culture_Art'],
        'known_languages': [],
        'excluded_places': [],
        'popularity_preference': 'Less Crowded'
    }

    model_weights = {
        'weather': 0, 
        'budget': 0,
        'attractions_quantity': 0,
        'attractions_quality': 0,
        'safety': 2,
        'attractions_popularity': -1, # Waga ujemna dla "Less Crowded"
        'english_level': 0,
        'known_languages': 0.0,
        'distance': 00,
        'cuisine_quality': 0
    }
    
    print("--- Twoje preferencje ---")
    print(user_preferences)
    print("\n--- Obliczam rekomendacje... ---")
    recommendations = get_recommendations(user_preferences, model_weights)
    
    if recommendations is not None:
        print("\n--- Top 10 Rekomendacji ---")
        recommendations.rename(columns={'Country_x': 'Country'}, inplace=True)
        print(recommendations.to_string(index=False))