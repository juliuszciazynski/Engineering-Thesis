import pandas as pd
import sqlite3
import re

print("DATA PROCESSING - START")

#IMPORTING CSV FILES, AND CREATING DATABASE
file_dest_countries = "destinations_important_14_07_wersja_python_1.xlsx - Destination_Countries.csv"
file_country_stats = "destinations_important_14_07_wersja_python_1.xlsx - Country_Statistics.csv"
file_dest_stats = "destinations_important_14_07_wersja_python_1.xlsx - Destination_Statistics.csv"
file_attractions = "destinations_important_14_07_wersja_python_1.xlsx - Attractions.csv"
db_name = "travel_recommendation_final.db"
#DEFINING POPULARITY THRESHOLD
try:
    temp_df = pd.read_csv(file_attractions, encoding='latin-1', sep=';', usecols=['No_votes'])
    TOP_200_THRESHOLD = temp_df['No_votes'].nlargest(200).min()
    print(f"Threshold for Top 200 attractions set to: {TOP_200_THRESHOLD} votes.")
except Exception as e:
    print(f"Could not determine popularity threshold, using default value. Error: {e}")
    TOP_200_THRESHOLD = 14000

#MAPPING CATEGORIES 
definitive_mapping = {
    'Points of Interest': ['Landmark'], 'Landmarks': ['Landmark'], 'Speciality Museums': ['Museums'],
    'Historic Sites': ['Historic_Heritage'], 'Beaches': ['Beach', 'Nature_Recreation'],
    'Architectural Buildings': ['Culture_Art'], 'History Museums': ['Museums', 'Historic_Heritage'],
    'Art Museums': ['Museums', 'Culture_Art'], 'Cathedrals': ['Religion', 'Culture_Art', 'Landmark'],
    'Churches': ['Religion', 'Culture_Art'], 'Neighborhoods': ['Shopping_Urban'],
    'Castles': ['Historic_Heritage', 'Landmark'], 'Historic Walking Areas': ['Historic_Heritage'],
    'Religious Sites': ['Religion'], 'Bodies of Water': ['Nature_Recreation'], 'Parks': ['Nature_Recreation'],
    'Gardens': ['Nature_Recreation'], 'Mountains': ['Mountains_and_trails', 'Nature_Recreation'],
    'Ancient Ruins': ['Historic_Heritage'], 'Nature': ['Nature_Recreation'], 'Wildlife Areas': ['Nature_Recreation'],
    'Monuments': ['Historic_Heritage', 'Culture_Art'], 'Statues': ['Historic_Heritage', 'Culture_Art'],
    'Amusement': ['Entertainment_Leisure'], 'Theme Parks': ['Entertainment_Leisure'],
    'Lookouts': ['Landmark', 'Nature_Recreation'], 'Shopping Malls': ['Shopping_Urban'],
    'Flea': ['Shopping_Urban'], 'Street Markets': ['Shopping_Urban'], 'Zoos': ['Entertainment_Leisure', 'Nature_Recreation'],
    'Ski': ['Winter_Sports', 'Nature_Recreation'], 'Snowboard Areas': ['Winter_Sports', 'Nature_Recreation'],
    'Bridges': ['Scenic_Transport', 'Landmark'], 'Geologic Formations': ['Nature_Recreation'],
    'Caverns': ['Nature_Recreation'], 'Caves': ['Nature_Recreation'], 'Observation Decks': ['Landmark'],
    'Theaters': ['Culture_Art'], 'Towers': ['Landmark', 'Shopping_Urban'],
    'Military Museums': ['Museums', 'Historic_Heritage'], 'Hiking Trails': ['Mountains_and_trails', 'Nature_Recreation'],
    'Science Museums': ['Museums', 'Science_Technology'], 'Vineyards': ['Food_Drink', 'Nature_Recreation'],
    'Wineries': ['Food_Drink', 'Nature_Recreation'], 'Waterfalls': ['Nature_Recreation'],
    'Arenas': ['Entertainment_Leisure'], 'Islands': ['Nature_Recreation'], 'Stadiums': ['Entertainment_Leisure'],
    'Aquariums': ['Entertainment_Leisure', 'Nature_Recreation'], 'Art Galleries': ['Culture_Art'],
    'National Parks': ['Nature_Recreation'], 'Trams': ['Scenic_Transport'],
    'Natural History Museums': ['Museums', 'Nature_Recreation'], 'Water Parks': ['Entertainment_Leisure'],
    'Breweries': ['Food_Drink'], "Children's Museums": ['Museums', 'Entertainment_Leisure'],
    'Boardwalks': ['Shopping_Urban'], 'Piers': ['Shopping_Urban'], 'Cemeteries': ['Historic_Heritage'],
    'Distilleries': ['Food_Drink'], 'Libraries': ['Culture_Art'], 'Scenic Drives': ['Scenic_Transport'],
    'Entertainment Centers': ['Entertainment_Leisure'], 'Farms': ['Food_Drink', 'Nature_Recreation'],
    'Game': ['Entertainment_Leisure'], 'Thermal Spas': ['Entertainment_Leisure'],
    'Farmers Markets': ['Food_Drink', 'Shopping_Urban'], 'Government Buildings': ['Culture_Art', 'Historic_Heritage'],
    'Scenic Walking Areas': ['Nature_Recreation'], 'Ferries': ['Scenic_Transport'],
    'Rail Services': ['Scenic_Transport'], 'Scenic Railroads': ['Scenic_Transport'], 'Canyons': ['Nature_Recreation'],
    'Fountains': ['Culture_Art', 'Shopping_Urban'], 'Operas': ['Culture_Art'], 'Valleys': ['Nature_Recreation'],
    'Cultural Events': ['Culture_Art'], 'Sports Complexes': ['Entertainment_Leisure'],
    'Mines': ['Historic_Heritage', 'Science_Technology'], 'Visitor Centers': ['Culture_Art'],
    'Casinos': ['Entertainment_Leisure'], 'Forests': ['Nature_Recreation'], 'Geysers': ['Nature_Recreation'],
    'Hot Springs': ['Nature_Recreation'], 'Lighthouses': ['Landmark', 'Scenic_Transport'],
    'Marinas': ['Scenic_Transport'], 'Playgrounds': ['Entertainment_Leisure'], 'Volcanos': ['Nature_Recreation'],
    'Beach': ['Beach', 'Nature_Recreation'], 'Concerts': ['Culture_Art', 'Entertainment_Leisure'],
    'Convention Centers': ['Culture_Art'], 'Department Stores': ['Shopping_Urban'],
    'Educational sites': ['Culture_Art'], 'Gift Shops': ['Shopping_Urban'], 'Military Bases': ['Historic_Heritage'],
    'Pool Clubs': ['Entertainment_Leisure'], 'Spas': ['Entertainment_Leisure'],
    'Auto Racing Tracks': ['Entertainment_Leisure'], 'Battlefields': ['Historic_Heritage'],
    'Biking Trails': ['Nature_Recreation'], 'Civic Centres': ['Culture_Art', 'Shopping_Urban'],
    'Dams': ['Landmark', 'Science_Technology'], 'Factory Outlets': ['Shopping_Urban'],
    'Mysterious Sites': ['Historic_Heritage', 'Culture_Art'], 'Public Transportation Systems': ['Scenic_Transport'],
    'Safaris': ['Entertainment_Leisure', 'Nature_Recreation'], 'Ships': ['Historic_Heritage', 'Scenic_Transport'],
    'Coffeehouses': ['Food_Drink'], 'Disney Parks': ['Entertainment_Leisure'],
    'Observatories': ['Science_Technology', 'Entertainment_Leisure'], 'Planetariums': ['Science_Technology', 'Entertainment_Leisure'],
    'Symphonies': ['Culture_Art'], 'Antique Shops': ['Shopping_Urban'], 'Beach & Pool Clubs': ['Entertainment_Leisure', 'Beach'],
    'Character Experiences': ['Entertainment_Leisure'], 'Cooking Classes': ['Food_Drink'],
    'Deserts': ['Nature_Recreation'], 'Dinner Theaters': ['Culture_Art', 'Food_Drink'],
    'Drink Festivals': ['Food_Drink'], 'Equestrian Trails': ['Nature_Recreation'], 'Exhibitions': ['Culture_Art'],
    'Food': ['Food_Drink'], 'Geologic Forms': ['Nature_Recreation'], 'Horse Tracks': ['Entertainment_Leisure'],
    'Military Museum': ['Museums', 'Historic_Heritage'], 'Missions': ['Historic_Heritage', 'Religion'],
    'Movie Theaters': ['Entertainment_Leisure'], 'Nature & Wildlife Areas': ['Nature_Recreation'],
    'Other Outdoor Activities': ['Nature_Recreation', 'Entertainment_Leisure'], 'Shuttles': ['Scenic_Transport'],
    'Speciality & Gift Shops': ['Shopping_Urban'], 'Taxis': ['Scenic_Transport'], 'Points of I': ['Landmark']
}
#DATA LOADING AND BASIC CLEANING
try:
    print("Loading CSV files...")
    df_dest_countries = pd.read_csv(file_dest_countries, encoding='latin-1', sep=';')
    df_country_stats = pd.read_csv(file_country_stats, encoding='latin-1', sep=';')
    df_dest_stats = pd.read_csv(file_dest_stats, encoding='latin-1', sep=';')
    df_attractions = pd.read_csv(file_attractions, encoding='latin-1', sep=';')
    print("Files loaded successfully.")
    def clean_name_func(name):
        return str(name).strip().replace('Finlandia', 'Finland').replace('Czech Republic', 'Czechia')
    for df in [df_dest_countries, df_country_stats, df_dest_stats, df_attractions]:
        for col in ['Destination', 'Country']:
            if col in df.columns:
                df[col] = df[col].apply(clean_name_func)
    popularity_counts = df_attractions.groupby('Destination')['No_votes'].sum().reset_index()
    popularity_counts.rename(columns={'No_votes': 'Popularity_TripAdvisor_Count'}, inplace=True)
except Exception as e:
    print(f"Error during loading or basic data cleaning: {e}")
    exit()

#ATTRACTION TYPES, all categories from 'Attraction type' column will be grouped into final categories
print("Grouping attraction categories...")
final_group_columns = [
    'Historic_Heritage', 'Religion', 'Nature_Recreation', 'Culture_Art', 'Museums',
    'Entertainment_Leisure', 'Shopping_Urban', 'Food_Drink', 'Winter_Sports',
    'Scenic_Transport', 'Science_Technology', 'Beach', 'Mountains_and_trails',
    'Landmark', 'Top_200_Popular'
]
grouped_features = pd.DataFrame(0, index=df_attractions.index, columns=final_group_columns)
df_attractions.dropna(subset=['Attraction type'], inplace=True)
df_attractions['Attraction type'] = df_attractions['Attraction type'].astype(str)
#PROCESSING EACH ROW
for index, row in df_attractions.iterrows():
    if row['Attraction type'] == '#N/A':
        continue
        
    detailed_types = row['Attraction type'].split('\x95')
    
    for detailed_type in detailed_types:
        cleaned_detailed_type = detailed_type.strip()
        
        if cleaned_detailed_type in definitive_mapping:
            groups_to_assign = definitive_mapping[cleaned_detailed_type]
            for group in groups_to_assign:
                if group in grouped_features.columns:
                    grouped_features.loc[index, group] = 1

print("Applying popularity rule for 'Top_200_Popular'...")
landmark_indices = df_attractions[df_attractions['No_votes'] >= TOP_200_THRESHOLD].index
grouped_features.loc[landmark_indices, 'Top_200_Popular'] = 1

df_attractions_processed = pd.concat([df_attractions.drop('Attraction type', axis=1), grouped_features], axis=1)
print("Grouping finished.")

#FINAL MERGING
print("Preparing final tables...")
df_main_destinations = pd.merge(df_dest_countries, df_country_stats, on='Country', how='left')
df_main_destinations = pd.merge(df_main_destinations, df_dest_stats, on=['Destination', 'Country'], how='left')
df_main_destinations = pd.merge(df_main_destinations, popularity_counts, on='Destination', how='left')

#CREATING SQL FROM CSV
def make_sql_safe_col_names(df_to_clean):

    df_to_clean.columns = [re.sub(r'[^a-zA-Z0-9_]', '', str(col)) for col in df_to_clean.columns]
    return df_to_clean

df_main_destinations = make_sql_safe_col_names(df_main_destinations)
df_attractions_processed_safe = make_sql_safe_col_names(df_attractions_processed.copy())
#SAVING TO DATABASE AND CSV
try:
    print(f"Saving data to database: {db_name}...")
    conn = sqlite3.connect(db_name)
    df_main_destinations.to_sql('destinations', conn, if_exists='replace', index=False)
    df_attractions_processed_safe.to_sql('attractions', conn, if_exists='replace', index=False)
    conn.commit()
    conn.close()
    print("Saving to database successful.")
    #WE WILL HAVE TWO FILES, DESTINATIONS AND ATTRACTIONS
    output_dest_csv = "final_destinations.csv"
    output_attr_csv = "final_attractions.csv"
    
    print(f"Saving processed data to CSV file: {output_dest_csv}...")
    df_main_destinations.to_csv(output_dest_csv, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"Saving processed data to CSV file: {output_attr_csv}...")
    df_attractions_processed.to_csv(output_attr_csv, index=False, sep=';', encoding='utf-8-sig')
    
    print("Saving to CSV files successful!")
except Exception as e:
    print(f"Error during save operation: {e}")
