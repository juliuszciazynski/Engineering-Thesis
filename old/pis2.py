import pandas as pd
from collections import Counter

# --- Definicja ścieżki do pliku ---
file_attractions = "destinations_important_14_07_wersja_python_1.xlsx - Attractions.csv"

print(f"Analizuję plik: {file_attractions}...")

try:
    # Wczytanie pliku CSV z odpowiednim kodowaniem i separatorem
    df_attractions = pd.read_csv(file_attractions, encoding='latin-1', sep=';')

    # --- Przetwarzanie kategorii ---

    # 1. Usuń wiersze, gdzie kategoria jest pusta (NaN)
    df_attractions.dropna(subset=['Attraction type'], inplace=True)

    # 2. Stwórz jedną długą listę wszystkich kategorii
    all_types_list = []
    
    # KRYTYCZNA POPRAWKA: Używamy wyrażenia regularnego do rozdzielania
    # r'\s{2,}' oznacza "rozdzielaj po znalezieniu dwóch lub więcej dowolnych białych znaków (spacji, tabulatorów etc.)"
    for item_list in df_attractions['Attraction type'].str.split(r'\s{2,}', regex=True):
        # Dalsza część logiki pozostaje bez zmian
        if item_list: # Upewnij się, że lista nie jest pusta
            all_types_list.extend([category.strip() for category in item_list if category.strip()])

    # 3. Zlicz wystąpienia każdej unikalnej kategorii
    type_counts = Counter(all_types_list)
    
    # 4. Znajdź unikalne kategorie i posortuj je alfabetycznie do wyświetlenia
    unique_types = sorted(list(type_counts.keys()))


    # --- Wyświetlenie wyników ---
    print("\n" + "="*50)
    print(f"Znaleziono {len(unique_types)} unikalnych kategorii atrakcji.")
    print("="*50 + "\n")

    print("Alfabetyczna lista wszystkich unikalnych kategorii wraz z liczbą wystąpień:")
    # Iterujemy po posortowanej liście kluczy, a wartość bierzemy ze słownika Counter
    for category in unique_types:
        print(f"- {category}  (wystąpień: {type_counts[category]})")

except FileNotFoundError:
    print(f"BŁĄD: Nie znaleziono pliku '{file_attractions}'. Upewnij się, że jest w dobrym folderze.")
except Exception as e:
    print(f"Wystąpił nieoczekiwany błąd: {e}")
