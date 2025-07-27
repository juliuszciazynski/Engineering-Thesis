import pandas as pd
import sqlite3

# --- 1. Definiowanie ścieżek do plików ---
# Upewnij się, że te nazwy plików są DOKŁADNIE takie same, jak Twoje przesłane pliki
# (np. z dopiskiem "wersja_python_1.xlsx - " na początku)
file_dest_countries = "destinations_important_14_07_wersja_python_1.xlsx - Destination_Countries.csv"
file_country_stats = "destinations_important_14_07_wersja_python_1.xlsx - Country_Statistics.csv"
file_dest_stats = "destinations_important_14_07_wersja_python_1.xlsx - Destination_Statistics.csv"
file_attractions = "destinations_important_14_07_wersja_python_1.xlsx - Attractions.csv"

# --- 2. Wczytanie plików CSV do DataFrame ---
print("Wczytywanie plików CSV...")
try:
    df_dest_countries = pd.read_csv(file_dest_countries, encoding='latin-1',sep=';')
    df_country_stats = pd.read_csv(file_country_stats, encoding='latin-1',sep=';')
    df_dest_stats = pd.read_csv(file_dest_stats, encoding='latin-1',sep=';')
    df_attractions = pd.read_csv(file_attractions, encoding='latin-1', sep=';')
    print("Pliki wczytane pomyślnie.")
except FileNotFoundError as e:
    print(f"Błąd: Nie znaleziono pliku. Upewnij się, że pliki są w tym samym katalogu co skrypt lub ścieżki są poprawne. Błąd: {e}")
    # Przerwanie wykonania, jeśli plik nie został znaleziony
    exit()

# --- 3. Czyszczenie i ujednolicanie nazw krajów/destynacji ---
# To jest KRYTYCZNY krok, który naprawi niespójności w nazewnictwie
def clean_name(name):
    if isinstance(name, str):
        return name.strip().replace('Finlandia', 'Finland').replace('Czech Republic', 'Czechia')
    return name

print("Ujednolicanie nazw destynacji i krajów...")

# Apply cleaning function to relevant columns in all DataFrames
df_dest_countries['Destination'] = df_dest_countries['Destination'].apply(clean_name)
df_dest_countries['Country'] = df_dest_countries['Country'].apply(clean_name)

df_country_stats['Country'] = df_country_stats['Country'].apply(clean_name)

df_dest_stats['Destination'] = df_dest_stats['Destination'].apply(clean_name)
df_dest_stats['Country'] = df_dest_stats['Country'].apply(clean_name)

df_attractions['Destination'] = df_attractions['Destination'].apply(clean_name)
df_attractions['Country'] = df_attractions['Country'].apply(clean_name)

# --- Dodatkowa weryfikacja ujednolicenia ---
# Tutaj możesz dodać printy, aby sprawdzić, czy ujednolicenie zadziałało
# np. print(df_dest_countries[df_dest_countries['Destination'].str.contains('Zagreb', na=False)])
# print(df_dest_stats[df_dest_stats['Country'].str.contains('Finland', na=False)])

# --- 4. Obliczanie Popularity_TripAdvisor_Count ---
print("Obliczanie Popularity_TripAdvisor_Count...")
popularity_counts = df_attractions.groupby('Destination')['No_votes'].sum().reset_index()
popularity_counts.rename(columns={'No_votes': 'Popularity_TripAdvisor_Count'}, inplace=True)

# --- 5. Obsługa brakujących wartości (NaN) i konwersja typów ---
print("Obsługa brakujących wartości i konwersja typów...")

# W Destination_Statistics: Distance_from_Lodz_km_road ma NaNs (było 'impossible')
# Będzie już float64 z NaN, więc wystarczy obsłużyć NaN np. fillna(0) lub pozostawić
# W tym przykładzie, na potrzeby bazy danych, NaNs w kolumnach liczbowych zostaną None (NULL w SQL) lub zostaną zmienione na 0.
# Jeśli chcesz je obsłużyć inaczej, zmień poniższą logikę.
# df_dest_stats['Distance_from_Lodz_km_road'].fillna(0, inplace=True) # przykład: zamiana NaN na 0

# W Country_Statistics: Wiele kolumn ma NaNs
# Tutaj również zamieniamy NaNs na 0 dla kolumn liczbowych, a English_level na 'Unknown'
numeric_cols_country_stats = [
    'Cost_of_Living_Index', 'Rent_Index', 'Cost_of_Living_Plus_Rent_Index', 'Groceries_Index',
    'Restaurant_Price_Index', 'Local_Purchasing_Power_Index', 'HDI_Value_Latest',
    'Life_Expectancy', 'GNI_per_capita_PPP', 'Inflation_Rate_National_Latest_Pct',
    'Crime_Index', 'Safety_Index', 'Unemployment_Rate_National_Latest_Pct'
]
for col in numeric_cols_country_stats:
    if col in df_country_stats.columns:
        df_country_stats[col] = pd.to_numeric(df_country_stats[col], errors='coerce') # Ensure numeric
        # df_country_stats[col].fillna(0, inplace=True) # przykład: zamiana NaN na 0

if 'English_level' in df_country_stats.columns:
    df_country_stats['English_level'].fillna('Unknown', inplace=True)

# --- 6. Łączenie DataFrame'ów dla głównej tabeli destynacji ---
print("Łączenie DataFrame'ów...")
# Łączymy df_dest_countries z df_country_stats po kolumnie 'Country'
df_main_destinations = pd.merge(df_dest_countries, df_country_stats, on='Country', how='left')

# Łączymy wynik z df_dest_stats po 'Destination' i 'Country'
df_main_destinations = pd.merge(df_main_destinations, df_dest_stats, on=['Destination', 'Country'], how='left')

# Dodajemy Popularity_TripAdvisor_Count
df_main_destinations = pd.merge(df_main_destinations, popularity_counts, on='Destination', how='left')

# Przykładowy podgląd po połączeniu
print("\n--- Podgląd połączonej tabeli 'Destinations' ---")
print(df_main_destinations.head())
print("\n--- Informacje o połączonej tabeli 'Destinations' ---")
print(df_main_destinations.info())

# --- Krok 2: Tworzenie bazy danych SQLite i ładowanie danych ---
print("\nTworzenie bazy danych SQLite i ładowanie danych...")
db_name = "travel_recommendation.db"
conn = sqlite3.connect(db_name)
cursor = conn.cursor()

# Tworzenie tabeli dla głównych destynacji
# (Możesz dostosować typy danych w SQL, np. TEXT, INTEGER, REAL)
# Na potrzeby przykładu używamy nazw kolumn z połączonego DataFrame

# Upewniamy się, że nazwy kolumn są poprawne dla SQL (np. bez znaków specjalnych, które mogłyby sprawić problem)
# Zastąp spacje i inne znaki w nazwach kolumn, jeśli takie by pozostały, aby były zgodne z SQL
df_main_destinations.columns = df_main_destinations.columns.str.replace('[^0-9a-zA-Z_]+', '', regex=True)
df_attractions.columns = df_attractions.columns.str.replace('[^0-9a-zA-Z_]+', '', regex=True)


# Ładowanie df_main_destinations do tabeli 'destinations'
# if_exists='replace' oznacza, że tabela zostanie nadpisana, jeśli już istnieje
print(f"Ładowanie danych do tabeli 'destinations' w {db_name}...")
df_main_destinations.to_sql('destinations', conn, if_exists='replace', index=False)
print("Dane załadowane do tabeli 'destinations'.")

# Ładowanie df_attractions do tabeli 'attractions'
print(f"Ładowanie danych do tabeli 'attractions' w {db_name}...")
df_attractions.to_sql('attractions', conn, if_exists='replace', index=False)
print("Dane załadowane do tabeli 'attractions'.")

# Potwierdzenie zmian i zamknięcie połączenia
conn.commit()
conn.close()
print(f"\nBaza danych {db_name} została pomyślnie utworzona i załadowana.")

# --- Krok 3: Przykładowe zapytanie do bazy danych (aby sprawdzić) ---
print("\n--- Przykładowe zapytanie do bazy danych (weryfikacja) ---")
conn_check = sqlite3.connect(db_name)
df_check_dest = pd.read_sql_query("SELECT Destination, Country, Overall_Daily_Cost_Budget_USD, Popularity_TripAdvisor_Count FROM destinations LIMIT 5;", conn_check)
print("\nPierwsze 5 wierszy z tabeli 'destinations':")
print(df_check_dest)

df_check_att = pd.read_sql_query("SELECT * FROM attractions LIMIT 102;", conn_check)
print("\nPierwsze 5 wierszy z tabeli 'attractions':")
print(df_check_att)

conn_check.close()
print("\nOperacje zakończone pomyślnie.")




import sqlite3
import pandas as pd

# Nazwa Twojej bazy danych SQLite
DB_NAME = "travel_recommendation.db"

print(f"Łączenie z bazą danych {DB_NAME} i eksportowanie danych do CSV...")

try:
    conn = sqlite3.connect(DB_NAME)

    # --- Eksport tabeli 'destinations' ---
    df_destinations = pd.read_sql_query("SELECT * FROM destinations;", conn)
    output_file_dest = "travel_recommendation_destinations.csv"
    df_destinations.to_csv(output_file_dest, index=False, encoding='utf-8', sep=';')
    print(f"Tabela 'destinations' została wyeksportowana do pliku: {output_file_dest}")

    # --- Eksport tabeli 'attractions' ---
    df_attractions = pd.read_sql_query("SELECT * FROM attractions;", conn)
    output_file_attr = "travel_recommendation_attractions.csv"
    df_attractions_processed = pd.read_sql_query("SELECT * FROM attractions;", conn) # Wczytujemy dane po OHE z bazy
    df_attractions_processed.to_csv(output_file_attr, index=False, encoding='utf-8', sep=';')
    print(f"Tabela 'attractions' została wyeksportowana do pliku: {output_file_attr}")

    conn.close()
    print("\nEksport zakończony pomyślnie. Pliki CSV są gotowe do przesłania.")

except FileNotFoundError:
    print(f"Błąd: Nie znaleziono pliku bazy danych '{DB_NAME}'. Upewnij się, że jest w tym samym katalogu co skrypt.")
except Exception as e:
    print(f"Wystąpił błąd podczas eksportowania danych: {e}")