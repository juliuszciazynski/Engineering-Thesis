import pandas as pd
from collections import Counter

# --- Definicja ścieżki do pliku ---
file_attractions = "destinations_important_14_07_wersja_python_1.xlsx - Attractions.csv"

print(f"Analizuję plik: {file_attractions}...")

try:
    # Wczytanie pliku CSV z odpowiednim kodowaniem i separatorem
    df_attractions = pd.read_csv(file_attractions, encoding='latin-1', sep=';')

    # --- Przetwarzanie kategorii ---

    # 1. Usuń wiersze, gdzie kolumna z typem atrakcji jest pusta (NaN)
    df_attractions.dropna(subset=['Attraction type'], inplace=True)

    # 2. Stwórz jedną długą listę wszystkich kategorii
    all_types_list = []
    
    # Rozdzielanie po zidentyfikowanym separatorze '\x95'
    for item_list in df_attractions['Attraction type'].str.split('\x95'):
        if item_list:
            all_types_list.extend([category.strip() for category in item_list if category.strip()])

    # 3. Zlicz wystąpienia każdej unikalnej kategorii
    type_counts = Counter(all_types_list)
    

    # --- Wyświetlenie wyników w formacie CSV (rozdzielone przecinkami) ---
    print("\n" + "="*50)
    print("Wyniki w formacie CSV (rozdzielone przecinkami):")
    print("="*50 + "\n")

    # 4. Konwersja obiektu Counter na DataFrame
    results_df = pd.DataFrame(type_counts.items(), columns=['Kategoria', 'Liczba Wystąpień'])

    # 5. Sortowanie DataFrame alfabetycznie po nazwie kategorii
    results_df.sort_values(by='Kategoria', inplace=True)

    # 6. Wyświetlenie DataFrame jako string w formacie CSV, bez indeksu
    # Metoda .to_csv() bez podania ścieżki do pliku zwraca string.
    # Domyślnym separatorem jest przecinek.
    print(results_df.to_csv(index=False))


except FileNotFoundError:
    print(f"BŁĄD: Nie znaleziono pliku '{file_attractions}'. Upewnij się, że jest w dobrym folderze.")
except Exception as e:
    print(f"Wystąpił nieoczekiwany błąd: {e}")
