import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import Toplevel
import pandas as pd
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from fredapi import Fred
import pyperclip
import os
import yfinance as yf
import requests
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import cm
from openpyxl import Workbook
from openpyxl.styles import Alignment
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import eurostat
from tkinter import  Toplevel
from tkinter import ttk
import re




fred_api = None
fmp_api_key = None

SETTINGS_FILE = "app_settings.json"

def set_modern_style(root):
    style = ttk.Style(root)

    # Ustawienia ogólne
    root.configure(bg="#1e1e2f")  # Tło aplikacji
    style.theme_use('default')

    # Styl przycisków
    style.configure("TButton", background="#2d2d44", foreground="#ffffff",
                    font=("Inter", 11, "bold"), padding=10, borderwidth=0, relief="flat")
    style.map("TButton", background=[("active", "#6366f1")], foreground=[("active", "#ffffff")])

    # Pola tekstowe i Combobox
    style.configure("TEntry", fieldbackground="#2d2d44", foreground="#ffffff", borderwidth=0, insertcolor="#ffffff")
    style.configure("SearchMode.TCombobox",
                    fieldbackground="#2d2d44",  # Tło pola wpisywania
                    background="#3c3c58",      # Tło rozwijanego menu
                    foreground="#ffffff",      # Kolor tekstu
                    borderwidth=1,
                    relief="flat")
    style.map("SearchMode.TCombobox",
              fieldbackground=[("readonly", "#2d2d44")],
              foreground=[("readonly", "#ffffff")],
              selectbackground=[("readonly", "#45455a")],
              selectforeground=[("readonly", "#ffffff")])

    # Globalne ustawienia dla Listbox używanego przez Combobox
    root.option_add("*TCombobox*Listbox*Background", "#3c3c58")  # Tło rozwijanego menu
    root.option_add("*TCombobox*Listbox*Foreground", "#ffffff")  # Kolor tekstu
    root.option_add("*TCombobox*Listbox*SelectBackground", "#4c4cff")  # Tło aktywnego wyboru
    root.option_add("*TCombobox*Listbox*SelectForeground", "#ffffff")  # Tekst aktywnego wyboru
    root.option_add("*TCombobox*Listbox*Font", "Inter 10 bold") 
    style.configure("TScrollbar", background="#2d2d44", troughcolor="#1e1e2f", borderwidth=0)
    style.map("TScrollbar", background=[("active", "#6366f1")])

    # Tabele (Treeview)
    style.configure("Treeview", background="#2d2d44", foreground="#ffffff",
                    fieldbackground="#2d2d44", rowheight=25, font=("Inter", 10))
    style.configure("Treeview.Heading", background="#2d2d44", foreground="#ffffff",
                    font=("Inter", 12, "bold"))
    style.map("Treeview.Heading", background=[("active", "#4c4cff")])

    style.configure("TCombobox",
                fieldbackground="#2d2d44",  # Tło pola wyboru
                background="#1e1e2f",      # Tło całego widgetu
                foreground="#ffffff",      # Kolor tekstu
                arrowcolor="#ffffff",      # Kolor strzałki
                borderwidth=0,             # Brak ramki
                lightcolor="#6366f1",      # Kolor interakcji
                darkcolor="#1e1e2f")       # Kolor ramki zewnętrznej

    style.map("TCombobox",
            fieldbackground=[("readonly", "#2d2d44"), ("focus", "#3c3c50")],  # Zmiana tła w trybie readonly i focus
            foreground=[("disabled", "#888888"), ("readonly", "#ffffff")],   # Kolor tekstu dla stanu readonly
            lightcolor=[("focus", "#6366f1")],                                # Kolor interakcji
            darkcolor=[("focus", "#6366f1")])       

class DataSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Data Search")
        self.root.state('zoomed')


        # Zastosowanie nowoczesnego stylu
        set_modern_style(self.root)

        # Initialize sort state for each column
        self.sort_states = {}
        self.root.option_add("*Font", "Inter 10")

        # Store search results, favorites, and search history
        self.search_results = pd.DataFrame()
        self.favorites = pd.DataFrame(columns=['id', 'title', 'frequency', 'source'])
        self.search_history = []
        self.history_index = -1
        self.sort_state = None  # Stores column sort state
        
        # Current search mode
        self.search_mode_var = tk.StringVar(value='FRED')

        # Create the UI
        self.create_widgets()

        # Load previous settings after widgets are initialized
        self.load_settings()

        # Prompt for API keys if not set
        if not fred_api or not fmp_api_key:
            self.api_login_prompt()

        self.fred = Fred(api_key=f'{fred_api}')
        self.FMP_API_KEY = fmp_api_key
        self.FMP_BASE_URL = 'https://financialmodelingprep.com/api/v3'

    def create_widgets(self):
        # Pasek wyszukiwania i nawigacja
        search_frame = tk.Frame(self.root, bg="#1e1e2f")  # Tło paska wyszukiwania
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        # Pole tekstowe wyszukiwania
        self.search_var = tk.StringVar()
        search_label = tk.Label(search_frame, text="Search:", bg="#1e1e2f", fg="#ffffff", font=("Inter", 12))
        search_label.pack(side=tk.LEFT)

        search_entry = tk.Entry(search_frame, textvariable=self.search_var, bg="#2d2d44", fg="#ffffff",
                                insertbackground="#ffffff", relief="flat", font=("Inter", 10))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind('<Return>', self.search_data)

        # Przyciski nawigacji (poprzednie/następne)
        prev_button = ttk.Button(search_frame, text="⬅", command=self.prev_search, style="Search.TButton")
        prev_button.pack(side=tk.LEFT, padx=5)

        next_button = ttk.Button(search_frame, text="➡", command=self.next_search, style="Search.TButton")
        next_button.pack(side=tk.LEFT, padx=5)

        # Przycisk wyszukiwania
        search_button = ttk.Button(search_frame, text="Search", command=self.search_data, style="Search.TButton")
        search_button.pack(side=tk.LEFT, padx=5)

        # ComboBox wyboru źródła danych
        self.search_mode_var = tk.StringVar(value="FRED")  # Domyślny tryb wyszukiwania
        self.search_mode_var.trace_add("write", self.on_search_mode_change)  # Dodanie śledzenia zmian

        search_mode_label = tk.Label(search_frame, text="Data Source:", bg="#1e1e2f", fg="#ffffff", font=("Inter", 12))
        search_mode_label.pack(side=tk.LEFT, padx=5)

        search_mode_combobox = ttk.Combobox(search_frame, textvariable=self.search_mode_var,
                                            values=['FRED', 'Stocks', 'Eurostat', 'World Bank'], state='readonly',
                                            style="SearchMode.TCombobox", width=12)
        search_mode_combobox.pack(side=tk.LEFT)

        style = ttk.Style()
        style.configure("TPanedwindow", background="#1e1e2f")  # Tło PanedWindow
        style.configure("TPanedwindow.Separator", background="#1e1e2f", borderwidth=0, sashrelief="flat")
        style.map("TPanedwindow.Separator", background=[("active", "#1e1e2f")])

        # PanedWindow dla dynamicznego podziału
        paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL, style="TPanedwindow")
        paned_window.pack(fill=tk.BOTH, expand=True)

        # Styl separatora (usuwa biały pasek)
        style = ttk.Style()
        style.configure("TSeparator", background="#1e1e2f")  # Dopasowanie do tła

        # Tabela wyników wyszukiwania
        self.table_frame = tk.Frame(paned_window, bg="#1e1e2f")  # Tło dla tabeli wyników
        paned_window.add(self.table_frame, weight=1)  # Główna część aplikacji

        self.tree = ttk.Treeview(self.table_frame, show='headings', style="Treeview")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Pionowy pasek przewijania dla tabeli wyników
        scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.tree.yview, style="TScrollbar")
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Inicjalizacja kolumn TreeView
        self.update_treeview_columns()

        # Panel ulubionych z rozszerzoną funkcjonalnością
        self.favorites_frame = tk.Frame(paned_window, bg="#1e1e2f", width=0)  # Stała początkowa szerokość
        paned_window.add(self.favorites_frame)  # Dodanie jako panelu do PanedWindow

        favorites_label = tk.Label(self.favorites_frame, text="", bg="#1e1e2f", fg="#ffffff", font=("Inter", 10))
        favorites_label.pack()

        # TreeView dla ulubionych
        self.favorites_tree = ttk.Treeview(self.favorites_frame, columns=("ID", "Title", "Frequency", "Source"), show="headings")
        self.favorites_tree.heading("ID", text="ID")
        self.favorites_tree.heading("Title", text="Title")
        self.favorites_tree.heading("Frequency", text="Frequency")
        self.favorites_tree.heading("Source", text="Source")
        self.favorites_tree.pack(fill=tk.BOTH, expand=True)

        # Pionowy pasek przewijania dla ulubionych
        favorites_scrollbar = ttk.Scrollbar(self.favorites_frame, orient=tk.VERTICAL, command=self.favorites_tree.yview, style="TScrollbar")
        self.favorites_tree.configure(yscroll=favorites_scrollbar.set)
        favorites_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Przyciski do zarządzania ulubionymi
        copy_button = ttk.Button(self.favorites_frame, text="Copy Codes", command=self.copy_favorites, style="Search.TButton")
        copy_button.pack(pady=5)

        generate_button = ttk.Button(self.favorites_frame, text="Generate Python Code", command=self.generate_python_code, style="Search.TButton")
        generate_button.pack(pady=5)

        remove_button = ttk.Button(self.favorites_frame, text="Remove Selected", command=self.remove_favorite, style="Search.TButton")
        remove_button.pack(pady=5)

        # Skróty klawiaturowe
        self.favorites_tree.bind('<Delete>', self.remove_favorite)
        self.root.bind('<Control-c>', self.copy_selected_row)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def update_treeview_columns(self, *args):
        search_mode = self.search_mode_var.get()
        if search_mode == 'FRED':
            columns = ('id', 'title', 'observation_start', 'observation_end', 'frequency_short', 'units')
            headings = {'id': 'ID', 'title': 'Title', 'observation_start': 'Observation Start', 'observation_end': 'Observation End', 'frequency_short': 'Frequency', 'units': 'Units'}
            column_widths = {'id': 100, 'title': 250, 'observation_start': 150, 'observation_end': 150, 'frequency_short': 100, 'units': 100}
        elif search_mode == 'Stocks':
            columns = ('symbol', 'name', 'stockExchange')
            headings = {'symbol': 'Symbol', 'name': 'Name', 'stockExchange': 'Exchange'}
            column_widths = {'symbol': 150, 'name': 250, 'stockExchange': 150}
        elif search_mode == 'Eurostat':
            columns = ('id', 'title', 'last update', 'data start', 'data end')
            headings = {'id': 'ID', 'title': 'Title', 'last update': 'Last Update', 'data start': 'Data Start', 'data end': 'Data End'}
            column_widths = {'id': 150, 'title': 250, 'last update': 150, 'data start': 100, 'data end': 100}
        elif search_mode == 'World Bank':
            columns = ('id', 'name', 'sourceNote', 'sourceOrganization')
            headings = {'id': 'ID', 'name': 'Name', 'sourceNote': 'Source Note', 'sourceOrganization': 'Source Organization'}
            column_widths = {'id': 150, 'name': 300, 'sourceNote': 400, 'sourceOrganization': 200}

            self.tree['columns'] = columns
            for col in columns:
                # Bind the sort_column method to the header click event
                self.tree.heading(col, text=headings[col], command=lambda _col=col: self.sort_column(_col))
                self.tree.column(col, width=column_widths[col])

            # Clear existing data
            self.tree.delete(*self.tree.get_children())

                # Clear existing columns
        self.tree['columns'] = columns
        for col in columns:
            # Bind the sort_column method to the header click event
            self.tree.heading(col, text=headings[col], command=lambda _col=col: self.sort_column(_col))
            self.tree.column(col, width=column_widths[col])

        # Clear existing data
        self.tree.delete(*self.tree.get_children())

    def search_data(self, event=None):
        search_query = self.search_var.get().strip()

        if not search_query:
            messagebox.showwarning("Warning", "Please enter a search query.")
            return

        # Save the query to history
        if self.history_index == -1 or (self.history_index >= 0 and self.search_history[self.history_index] != search_query):
            self.search_history.append(search_query)
            self.history_index = len(self.search_history) - 1

        search_mode = self.search_mode_var.get()

        if search_mode == 'FRED':
            # Reset the frequency filter
            frequency_filter = None

            # Split the query into words
            query_tokens = search_query.split()

            # Check for frequency filters at the end of the query
            if query_tokens[-1].upper() == 'Q':
                frequency_filter = 'Quarterly'
                search_query = ' '.join(query_tokens[:-1])
            elif query_tokens[-1].upper() == 'A':
                frequency_filter = 'Annual'
                search_query = ' '.join(query_tokens[:-1])
            elif query_tokens[-1].upper() == 'M':
                frequency_filter = 'Monthly'
                search_query = ' '.join(query_tokens[:-1])
            elif query_tokens[-1].upper() == 'D':
                frequency_filter = 'Daily'
                search_query = ' '.join(query_tokens[:-1])

            # Search FRED data
            try:
                if frequency_filter:
                    self.search_results = pd.DataFrame(self.fred.search(search_query, filter=('frequency', frequency_filter)))
                else:
                    self.search_results = pd.DataFrame(self.fred.search(search_query))

                # Clear the table and reset sorting
                self.tree.delete(*self.tree.get_children())
                self.sort_state = None

                # Insert results into the table
                for idx, row in self.search_results.iterrows():
                    self.tree.insert('', 'end', values=(row['id'], row['title'], row['observation_start'], row['observation_end'], row['frequency_short'], row['units']))

                # Bind double-click event to add to favorites
                self.tree.bind("<Double-1>", self.add_to_favorites)

            except Exception as e:
                messagebox.showerror("Error", f"An error occurred during the search: {e}")

        elif search_mode == 'Stocks':
            try:
                url = f"{self.FMP_BASE_URL}/search"
                params = {
                    'query': search_query,
                    'limit': 50,
                    'apikey': self.FMP_API_KEY
                }
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        # Create DataFrame
                        self.search_results = pd.DataFrame(data)
                        # Ensure columns exist before selecting
                        expected_columns = ['symbol', 'name', 'stockExchange']
                        self.search_results = self.search_results.reindex(columns=expected_columns)

                        # Replace NaN with empty strings
                        self.search_results.fillna('', inplace=True)
                    else:
                        messagebox.showinfo("Info", "No results found.")
                        self.tree.delete(*self.tree.get_children())
                        return
                else:
                    messagebox.showerror("Error", f"Failed to search stocks: {response.status_code}")
                    return

                # Clear existing data
                self.tree.delete(*self.tree.get_children())

                # Update columns for stock search
                self.update_treeview_columns()

                # Insert new data
                for idx, row in self.search_results.iterrows():
                    self.tree.insert('', 'end', values=(row['symbol'], row['name'], row['stockExchange']))

                # Bind double-click event to add to favorites
                self.tree.bind("<Double-1>", self.add_to_favorites)

            except Exception as e:
                messagebox.showerror("Error", f"An error occurred during the search: {e}")

        elif search_mode == 'Eurostat':
            try:
                import eurostat
                # Pobierz tabelę wszystkich dostępnych zbiorów danych
                toc = eurostat.get_toc_df()

                # Filtruj dane według zapytania
                filtered_toc = toc[toc['title'].str.contains(search_query, case=False, na=False)]

                if filtered_toc.empty:
                    messagebox.showinfo("Info", "No results found.")
                    return

                # Wybierz odpowiednie kolumny do wyświetlenia w tabeli
                self.search_results = filtered_toc[['code', 'title', 'last update of data', 'data start', 'data end']].rename(
                    columns={
                        'code': 'id',
                        'title': 'title',
                        'last update of data': 'last update',
                        'data start': 'data start',
                        'data end': 'data end'
                    }
                )

                # Wyświetl wyniki w tabeli
                self.tree.delete(*self.tree.get_children())
                for _, row in self.search_results.iterrows():
                    self.tree.insert('', 'end', values=(row['id'], row['title'], row['last update'], row['data start'], row['data end']))

                self.tree.bind("<Double-1>", self.add_to_favorites)

            except Exception as e:
                messagebox.showerror("Error", f"An error occurred during the search: {e}")

        elif search_mode == 'World Bank':
            try:
                # Tworzenie nowego okna z paskiem postępu
                progress_window = tk.Toplevel(self.root)
                progress_window.title("Loading Data")
                progress_window.geometry("350x100")
                progress_window.transient(self.root)  # Okno na wierzchu głównego
                progress_window.grab_set()  # Ustawienie focusu na nowe okno
                progress_window.resizable(False, False)  # Wyłączenie możliwości zmiany rozmiaru okna
                progress_window.protocol("WM_DELETE_WINDOW", lambda: None)  # Uniemożliwienie zamknięcia okna

                # Obliczanie środka okna głównego, aby ustawić okno postępu centralnie
                x_center = self.root.winfo_x() + (self.root.winfo_width() // 2) - 175
                y_center = self.root.winfo_y() + (self.root.winfo_height() // 2) - 50
                progress_window.geometry(f"+{x_center}+{y_center}")

                # Dodanie paska postępu
                progress = ttk.Progressbar(progress_window, orient='horizontal', length=300, mode='determinate')
                progress.pack(pady=30)
                progress["value"] = 0

                # Aktualizacja okna postępu, aby było widoczne od razu po otwarciu
                progress_window.update()  # Zamiast update_idletasks użyjemy pełnego update()

                # API World Bank URL
                url = "http://api.worldbank.org/v2/indicator"
                params = {
                    'format': 'json',
                    'per_page': 1000,
                    'page': 1
                }

                all_indicators = []
                total_pages = 1  # Inicjalizacja liczby stron

                while params['page'] <= total_pages:
                    response = requests.get(url, params=params)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if len(data) > 1:
                                indicators_data = data[1]
                                all_indicators.extend(indicators_data)

                                # Aktualizacja wartości paska postępu
                                if 'pages' in data[0]:
                                    total_pages = data[0]['pages']
                                progress["value"] = (params['page'] / total_pages) * 100
                                progress_window.update()  # Odświeżenie okna postępu po każdej aktualizacji

                                # Sprawdzenie, czy są więcej stron danych
                                if 'page' in data[0] and data[0]['page'] < total_pages:
                                    params['page'] += 1
                                else:
                                    break
                            else:
                                break
                        except ValueError:
                            messagebox.showerror("Error", "Failed to decode JSON response.")
                            progress_window.destroy()  # Zamknięcie okna w przypadku błędu
                            return
                    else:
                        messagebox.showerror("Error", f"Failed to search World Bank data: {response.status_code}")
                        progress_window.destroy()  # Zamknięcie okna w przypadku błędu
                        return

                # Zamknięcie okna paska postępu po zakończeniu
                progress_window.destroy()

                # Konwersja do DataFrame
                all_indicators_df = pd.DataFrame(all_indicators)

                # Filtrowanie wyników na podstawie zapytania użytkownika
                search_query_lower = search_query.lower()
                filtered_indicators = all_indicators_df[all_indicators_df['name'].str.contains(search_query_lower, case=False, na=False)]

                # Wybranie odpowiednich kolumn
                self.search_results = filtered_indicators[['id', 'name', 'sourceNote', 'sourceOrganization']]

                # Wyczyszczenie istniejących danych w tabeli
                self.tree.delete(*self.tree.get_children())

                # Aktualizacja kolumn TreeView dla wyników z Banku Światowego
                self.update_treeview_columns()

                # Wstawienie wyników do tabeli
                for idx, row in self.search_results.iterrows():
                    self.tree.insert('', 'end', values=(row['id'], row['name'], row['sourceNote'], row['sourceOrganization']))

                # Obsługa podwójnego kliknięcia do dodania do ulubionych
                self.tree.bind("<Double-1>", self.add_to_favorites)

            except Exception as e:
                # Wyświetlenie błędu i zamknięcie okna postępu
                messagebox.showerror("Error", f"An error occurred during the search: {e}")
                if 'progress_window' in locals():
                    progress_window.destroy()

    def prev_search(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.search_var.set(self.search_history[self.history_index])

    def set_modern_style(root):
        style = ttk.Style(root)

        # Global style settings
        root.configure(bg="#1e1e2f")  # Background color

        # General settings
        style.theme_use('default')
        style.configure("TButton", background="#2d2d44", foreground="#ffffff",
                        font=("Inter", 10), padding=10, borderwidth=0)
        style.map("TButton", background=[("active", "#6366f1")], foreground=[("active", "#ffffff")])

        style.configure("TLabel", background="#1e1e2f", foreground="#ffffff", font=("Inter", 10))
        style.configure("TEntry", fieldbackground="#2d2d44", foreground="#ffffff",
                        font=("Inter", 10), padding=5, borderwidth=0)
        style.configure("Treeview", background="#2d2d44", foreground="#ffffff", rowheight=25,
                        fieldbackground="#2d2d44", font=("Inter", 10), borderwidth=0)
        style.configure("Treeview.Heading", background="#6366f1", foreground="#ffffff",
                        font=("Inter", 10, "bold"))

        # Custom scrollbar style
        style.configure("TScrollbar", background="#2d2d44", troughcolor="#1e1e2f", borderwidth=0)
        style.map("TScrollbar", background=[("active", "#6366f1")])

        # Favorites frame settings
        root.option_add("*TFrame.background", "#1e1e2f")
        root.option_add("*TFrame.foreground", "#ffffff")

    def next_search(self):
        if self.history_index < len(self.search_history) - 1:
            self.history_index += 1
            self.search_var.set(self.search_history[self.history_index])

    def sort_column(self, column):
        if self.search_results.empty:
            return

        # Determine the sorting order
        if self.sort_states.get(column, 'none') == 'descending':
            self.sort_states[column] = 'ascending'
            ascending = True
        else:
            self.sort_states[column] = 'descending'
            ascending = False

        try:
            search_mode = self.search_mode_var.get()

            if search_mode == 'FRED':
                column_mapping = {
                    'ID': 'id',
                    'Title': 'title',
                    'Observation Start': 'observation_start',
                    'Observation End': 'observation_end',
                    'Frequency': 'frequency_short',
                    'Units': 'units',
                }
            elif search_mode == 'Stocks':
                column_mapping = {
                    'Symbol': 'symbol',
                    'Name': 'name',
                    'Exchange': 'stockExchange',
                }
            elif search_mode == 'Eurostat':
                column_mapping = {
                    'ID': 'id',
                    'Title': 'title',
                    'Last Update': 'last update',
                    'Data Start': 'data start',
                    'Data End': 'data end',
                }
            elif search_mode == 'World Bank':
                column_mapping = {
                    'ID': 'id',
                    'Name': 'name',
                    'Source Note': 'sourceNote',
                    'Source Organization': 'sourceOrganization',
                }
            else:
                column_mapping = {col: col for col in self.search_results.columns}

            df_column = column_mapping.get(column, column)
            if df_column not in self.search_results.columns:
                raise KeyError(f"Column '{column}' not found in the data.")

            # Sortuj dane
            self.search_results = self.search_results.sort_values(by=df_column, ascending=ascending)

            # Aktualizuj TreeView
            self.tree.delete(*self.tree.get_children())
            for _, row in self.search_results.iterrows():
                self.tree.insert('', 'end', values=row.tolist())

        except KeyError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to sort data: {e}")

    def update_treeview_columns(self, *args):
        search_mode = self.search_mode_var.get()
        if search_mode == 'FRED':
            columns = ('id', 'title', 'observation_start', 'observation_end', 'frequency_short', 'units')
            headings = {'id': 'ID', 'title': 'Title', 'observation_start': 'Observation Start', 'observation_end': 'Observation End', 'frequency_short': 'Frequency', 'units': 'Units'}
        elif search_mode == 'Stocks':
            columns = ('symbol', 'name', 'stockExchange')
            headings = {'symbol': 'Symbol', 'name': 'Name', 'stockExchange': 'Exchange'}
        elif search_mode == 'Eurostat':
            columns = ('id', 'title', 'last update', 'data start', 'data end')
            headings = {'id': 'ID', 'title': 'Title', 'last update': 'Last Update', 'data start': 'Data Start', 'data end': 'Data End'}
        elif search_mode == 'World Bank':
            columns = ('id', 'name', 'sourceNote', 'sourceOrganization')
            headings = {'id': 'ID', 'name': 'Name', 'sourceNote': 'Source Note', 'sourceOrganization': 'Source Organization'}
        else:
            columns = ()
            headings = {}

        # Aktualizacja kolumn TreeView
        self.tree['columns'] = columns
        for col in columns:
            self.tree.heading(col, text=headings[col], command=lambda _col=col: self.sort_column(_col))
            self.tree.column(col, anchor='w', width=150)

        # Wyczyszczenie istniejących danych
        self.tree.delete(*self.tree.get_children())

    def add_to_favorites(self, event):
        selected_item = self.tree.selection()
        if selected_item:
            item_data = self.tree.item(selected_item)
            item_values = item_data['values']

            search_mode = self.search_mode_var.get()

            if search_mode == 'FRED':
                # Extract columns: 'id', 'title', 'frequency_short', 'source'
                selected_columns = [item_values[0], item_values[1], item_values[4], 'FRED']
            elif search_mode == 'Stocks':
                # Extract columns: 'symbol', 'name', 'stockExchange', 'source'
                selected_columns = [item_values[0], item_values[1], item_values[2], 'Stocks']
            elif search_mode == 'Eurostat':
                selected_columns = [item_values[0], item_values[1], item_values[2], 'Eurostat']
            elif search_mode == 'World Bank':
                # Extract columns: 'id', 'name', 'sourceNote', 'sourceOrganization', 'source'
                selected_columns = [item_values[0], item_values[1], item_values[2], 'World Bank']

            # Sprawdzenie, czy 'source' jest w kolumnach ulubionych
            if 'source' not in self.favorites.columns:
                self.favorites['source'] = ''

            # Sprawdzenie, czy element już jest w ulubionych
            if not self.favorites[(self.favorites['id'] == item_values[0]) & (self.favorites['source'] == search_mode)].empty:
                messagebox.showinfo("Info", "Item already in favorites.")
                return

            # Dodanie do ulubionych
            self.favorites = pd.concat([self.favorites, pd.DataFrame([selected_columns], columns=['id', 'title', 'frequency', 'source'])], ignore_index=True)
            self.update_favorites_tree()

    def update_favorites_tree(self):
        # Clear the favorites TreeView
        self.favorites_tree.delete(*self.favorites_tree.get_children())
        # Insert data into the favorites TreeView
        for _, row in self.favorites.iterrows():
            self.favorites_tree.insert('', 'end', values=(row['id'], row['title'], row['frequency'], row['source']))

    def on_search_mode_change(self, *args):
        # Aktualizacja kolumn TreeView na podstawie trybu wyszukiwania
        self.update_treeview_columns()

        # Opcjonalnie możesz także wyczyścić dane w tabeli po zmianie trybu
        self.tree.delete(*self.tree.get_children())

    def remove_favorite(self, event=None):
        selected_items = self.favorites_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No items selected to remove.")
            return

        # Iterate over selected items and remove them from the DataFrame
        for selected_item in selected_items:
            item_data = self.favorites_tree.item(selected_item)
            item_id = item_data['values'][0]
            item_source = item_data['values'][3]

            # Ensure 'source' column exists
            if 'source' not in self.favorites.columns:
                self.favorites['source'] = ''

            # Remove the row from the DataFrame based on ID and source
            self.favorites = self.favorites[
                ~((self.favorites['id'] == item_id) & (self.favorites['source'] == item_source))
            ].reset_index(drop=True)

        # Update the TreeView
        self.update_favorites_tree()

    def copy_favorites(self):
        # Copy codes (id) to clipboard
        codes = '\n'.join(self.favorites['id'].tolist())
        self.root.clipboard_clear()
        self.root.clipboard_append(codes)
        messagebox.showinfo("Info", "Codes copied to clipboard.")

    def generate_python_code(self):
        if self.favorites.empty:
            messagebox.showwarning("Warning", "No favorites to generate code.")
            return

        code_lines = [
            "import pandas as pd",
            "from fredapi import Fred",
            "import yfinance as yf",
            "import re",
            "from eurostat import get_data_df",
            "import requests",
            "",
            "",
            "# Initialize data dictionary",
            "data_dict = {}",
            ""
        ]

        fred_items = self.favorites[self.favorites['source'] == 'FRED']
        stock_items = self.favorites[self.favorites['source'] == 'Stocks']
        eurostat_items = self.favorites[self.favorites['source'] == 'Eurostat']
        world_bank_items = self.favorites[self.favorites['source'] == 'World Bank']

        if not fred_items.empty:
            code_lines.append("# Fetching data from FRED")
            for _, row in fred_items.iterrows():
                code_lines.append(f"data_dict['{row['title']}'] = fred.get_series('{row['id']}')")
                code_lines.append("# Initialize FRED API",)
                code_lines.append(f"fred = Fred(api_key='{fred_api}')  # Replace with your FRED API key",)


        if not stock_items.empty:
            code_lines.append("# Fetching stock data using yfinance")
            for _, row in stock_items.iterrows():
                code_lines.append(f"data_dict['{row['title']}'] = yf.download('{row['id']}', period='max')['Close']")

        if not eurostat_items.empty:
            code_lines.append("# Fetching data from Eurostat and transforming it")
            for _, row in eurostat_items.iterrows():
                code_lines.extend([
                    f"raw_data = get_data_df('{row['id']}')",
                    "# Full country mapping for European countries",
                    "country_mapping = {",
                    "'AL': 'Albania', 'AT': 'Austria', 'BE': 'Belgium', 'BG': 'Bulgaria', 'CH': 'Switzerland',",
                    "'CY': 'Cyprus', 'CZ': 'Czechia', 'DE': 'Germany', 'DK': 'Denmark', 'EE': 'Estonia',",
                    "'EL': 'Greece', 'ES': 'Spain', 'FI': 'Finland', 'FR': 'France', 'HR': 'Croatia',",
                    "'HU': 'Hungary', 'IE': 'Ireland', 'IS': 'Iceland', 'IT': 'Italy', 'LT': 'Lithuania',",
                    "'LU': 'Luxembourg', 'LV': 'Latvia', 'MT': 'Malta', 'NL': 'Netherlands', 'NO': 'Norway',",
                    "'PL': 'Poland', 'PT': 'Portugal', 'RO': 'Romania', 'SE': 'Sweden', 'SI': 'Slovenia',",
                    "'SK': 'Slovakia', 'TR': 'Turkey', 'UK': 'United Kingdom', 'JP': 'Japan'",
                    "}",
                    "",
                    "date_columns = [col for col in raw_data.columns if col.startswith('geo') or re.match(r'^\\d{4}(-Q\\d|-M\\d{2})?$|^\\d{4}-\\d{2}$', col)]",
                    "raw_data = raw_data[date_columns]",
                    "raw_data.rename(columns={'geo\\TIME_PERIOD': 'geo'}, inplace=True)",
                    "raw_data['geo'] = raw_data['geo'].map(country_mapping).fillna(raw_data['geo'])",
                    "raw_data = raw_data.set_index('geo').T",
                    "raw_data.index = raw_data.index.map(",
                    "    lambda x: pd.to_datetime(f\"{x[:4]}-{int(x[-1])*3-2:02d}-01\") if '-Q' in x else (",
                    "    pd.to_datetime(x) if '-' in x else pd.to_datetime(f\"{x}-01-01\"))",
                    ")",
                    "raw_data.index.name = 'Date'",
                    "raw_data.reset_index(inplace=True)",
                    f"data_dict['{row['title']}'] = raw_data.set_index('Date')",
                ])

        if not world_bank_items.empty:
            code_lines.append("# Fetching data from World Bank API with enhanced diagnostics")
            for _, row in world_bank_items.iterrows():
                code_lines.extend([
                    f"indicator_id = '{row['id']}'",
                    "# Ensure correct format in the request",
                    "url = f'http://api.worldbank.org/v2/country/all/indicator/{indicator_id}'",
                    "params = {'format': 'json', 'per_page': 1000, 'page': 1}",
                    "all_data = []",
                    "",
                    "# Define the list of top 25 countries",
                    "top_25_countries = [",
                    "    'United States', 'China', 'Japan', 'Germany', 'India', 'United Kingdom',",
                    "    'France', 'Italy', 'Brazil', 'Canada', 'Russian Federation', 'Korea, Rep.',",
                    "    'Australia', 'Spain', 'Mexico', 'Indonesia', 'Netherlands', 'Saudi Arabia',",
                    "    'Turkey', 'Switzerland', 'Sweden', 'Poland', 'Belgium', 'Taiwan', 'Norway'",
                    "]",
                    "while True:",
                    "    response = requests.get(url, params=params)",
                    "    if response.status_code == 200:",
                    "        try:",
                    "            data = response.json()",
                    "",
                    "            if len(data) > 1:",
                    "                all_data.extend(data[1])",
                    "                if 'page' in data[0] and data[0]['page'] < data[0]['pages']:",
                    "                    params['page'] += 1",
                    "                else:",
                    "                    break",
                    "            else:",
                    "                break",
                    "        except ValueError as e:",
                    "            break",
                    "    else:",
                    "        break",
                    "",
                    "# Transform data and add to data_dict if valid",
                    "if all_data:",
                    "    df = pd.DataFrame(all_data)",
                    "    if 'country' in df.columns:",
                    "        df['country_name'] = df['country'].apply(lambda x: x['value'] if isinstance(x, dict) else x)",
                    "        df_filtered = df[df['country_name'].isin(top_25_countries)]",
                    "        df_filtered = df_filtered[['country_name', 'date', 'value']].dropna()",
                    "        df_filtered.rename(columns={'date': 'Date'}, inplace=True)",
                    "        df_filtered['Date'] = pd.to_datetime(df_filtered['Date'], errors='coerce')",
                    "        df_filtered = df_filtered.dropna(subset=['Date'])",
                    "        if not df_filtered.empty:",
                    "            df_pivot = df_filtered.pivot(index='Date', columns='country_name', values='value')",
                    f"            data_dict['{row['title']}'] = df_pivot",
                ])

        code_lines.append("# Combine all data into a single DataFrame if there is data in data_dict")
        code_lines.append("if data_dict:")
        code_lines.append("    df = pd.concat(data_dict.values(), axis=1, keys=data_dict.keys())")
        code_lines.append("    df_fill = df")
        code_lines.append("else:")
        code_lines.append("    None")

        python_code = '\n'.join(code_lines)

        # Copy Python code to clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(python_code)
        messagebox.showinfo("Info", "Python code copied to clipboard.")
    
    def copy_selected_row(self, event=None):
        # Copy the selected row in the main tree to the clipboard
        selected_item = self.tree.selection()
        if selected_item:
            item_data = self.tree.item(selected_item)
            item_values = item_data['values']
            pyperclip.copy(str(item_values))
            messagebox.showinfo("Info", "Row copied to clipboard.")

    def show_context_menu(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        search_mode = self.search_mode_var.get()

        context_menu = tk.Menu(self.root, tearoff=0)

        if search_mode == 'Eurostat':
            context_menu.add_command(label="Download", command=self.download_eurostat_data)
        else:
            context_menu.add_command(label="Download", command=self.download_series)

        context_menu.add_command(label="Show Plot", command=self.show_plot)

        if search_mode == 'Stocks':
            context_menu.add_command(label="Fundaments", command=self.show_fundamentals)
            context_menu.add_command(label="Download Fundamentals", command=self.download_fundamentals)

        context_menu.tk_popup(event.x_root, event.y_root)
   
    def download_series(self):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        item_data = self.tree.item(selected_item)
        item_values = item_data['values']
        search_mode = self.search_mode_var.get()

        if search_mode == 'FRED':
            series_id = item_values[0]
            try:
                # Pobieranie szeregu czasowego z FRED
                series = self.fred.get_series(series_id)

                # Zapis do pliku Excel
                filepath = os.path.join(os.getcwd(), f"{series_id}.xlsx")
                series.to_excel(filepath)
                messagebox.showinfo("Success", f"Series saved as {series_id}.xlsx")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to download series: {e}")

        elif search_mode == 'Stocks':
            symbol = item_values[0]
            try:
                # Pobieranie danych z yfinance
                data = yf.download(symbol, period='max')

                # Zapis do pliku Excel
                filepath = os.path.join(os.getcwd(), f"{symbol}.xlsx")
                data.to_excel(filepath)
                messagebox.showinfo("Success", f"Data saved as {symbol}.xlsx")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to download data: {e}")

        elif search_mode == 'World Bank':
            indicator_id = item_values[0]
            try:
                # Lista największych gospodarek
                top_25_countries = [
                    "United States", "China", "Japan", "Germany", "India", "United Kingdom",
                    "France", "Italy", "Brazil", "Canada", "Russian Federation", "Korea, Rep.",
                    "Australia", "Spain", "Mexico", "Indonesia", "Netherlands", "Saudi Arabia",
                    "Turkey", "Switzerland", "Sweden", "Poland", "Belgium", "Taiwan", "Norway"
                ]

                # Pobieranie danych z Banku Światowego
                url = f"http://api.worldbank.org/v2/country/all/indicator/{indicator_id}"
                params = {
                    'format': 'json',
                    'per_page': 1000,
                    'page': 1
                }
                all_data = []

                # Pobieranie wszystkich stron danych
                while True:
                    response = requests.get(url, params=params)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if len(data) > 1:
                                indicator_data = data[1]
                                all_data.extend(indicator_data)

                                # Sprawdzanie, czy są kolejne strony danych
                                if 'page' in data[0] and data[0]['page'] < data[0]['pages']:
                                    params['page'] += 1
                                else:
                                    break
                            else:
                                break
                        except ValueError:
                            messagebox.showerror("Error", "Failed to decode JSON response.")
                            return
                    else:
                        messagebox.showerror("Error", f"Failed to download data: {response.status_code}")
                        return

                # Tworzenie DataFrame z pełnymi danymi
                df = pd.DataFrame(all_data)

                # Filtrowanie tylko dla krajów z top 25 gospodarek
                if 'country' in df.columns:
                    df['country_name'] = df['country'].apply(lambda x: x['value'] if isinstance(x, dict) else x)
                    df = df[df['country_name'].isin(top_25_countries)]

                # Sprawdzenie dostępności danych
                if df.empty:
                    messagebox.showinfo("Info", "No data available for the selected indicator and countries.")
                    return

                # Przekształcenie danych do szerokiej tabeli
                df = df[['country_name', 'date', 'value']].dropna()
                df.rename(columns={'date': 'Date'}, inplace=True)
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')  # Konwersja dat na obiekty datetime
                df = df.dropna(subset=['Date'])  # Usunięcie niepoprawnych dat
                df_pivot = df.pivot(index='Date', columns='country_name', values='value')

                # Sprawdzenie dostępności danych po przekształceniu
                if df_pivot.empty:
                    messagebox.showinfo("Info", "No valid data available to download.")
                    return

                # Zapisanie danych do pliku Excel
                filename = os.path.join(os.getcwd(), f"{indicator_id}_top25.xlsx")
                df_pivot.to_excel(filename)
                messagebox.showinfo("Success", f"Data saved as {filename}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to download dataset: {e}")

    def show_plot(self):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        item_data = self.tree.item(selected_item)
        item_values = item_data['values']
        search_mode = self.search_mode_var.get()

        # Kolorystyka dopasowana do motywu
        background_color = "#2d2d44"
        axes_color = "#1e1e2f"
        grid_color = "#6366f1"
        text_color = "#ffffff"
        line_color = "#4caf50"

        def apply_plot_theme(ax, fig):
            """Apply consistent theme to all plots."""
            fig.patch.set_facecolor(background_color)
            ax.set_facecolor(axes_color)
            ax.grid(True, linestyle="--", linewidth=0.5, color=grid_color)
            ax.tick_params(axis='x', colors=text_color)
            ax.tick_params(axis='y', colors=text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(grid_color)

        if search_mode == 'FRED':
            series_id = item_values[0]
            try:
                series = self.fred.get_series(series_id)
                plot_window = Toplevel(self.root)
                plot_window.title(f"Plot: {series_id}")
                
                fig, ax = plt.subplots(figsize=(10, 6))
                apply_plot_theme(ax, fig)
                ax.plot(series.index, series.values, label=series_id, color=line_color, linewidth=2)
                ax.set_title(f"Series: {series_id}", fontsize=14, fontweight="bold", color=text_color)
                ax.set_xlabel("Date", fontsize=12, color=text_color)
                ax.set_ylabel("Value", fontsize=12, color=text_color)
                ax.legend(facecolor=axes_color, edgecolor=grid_color, fontsize=10, labelcolor=text_color)
                
                canvas = FigureCanvasTkAgg(fig, master=plot_window)
                canvas.draw()
                canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
                toolbar = NavigationToolbar2Tk(canvas, plot_window)
                toolbar.update()
                toolbar.pack(side=tk.TOP, fill=tk.X)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to display plot: {e}")

        elif search_mode == 'Stocks':
            symbol = item_values[0]
            try:
                data = yf.download(symbol, period='max')
                plot_window = Toplevel(self.root)
                plot_window.title(f"Plot: {symbol}")
                
                fig, ax = plt.subplots(figsize=(10, 6))
                apply_plot_theme(ax, fig)
                ax.plot(data.index, data['Close'], label="Close Price", color=line_color, linewidth=2)
                ax.set_title(f"Symbol: {symbol}", fontsize=14, fontweight="bold", color=text_color)
                ax.set_xlabel("Date", fontsize=12, color=text_color)
                ax.set_ylabel("Close Price", fontsize=12, color=text_color)
                ax.legend(facecolor=axes_color, edgecolor=grid_color, fontsize=10, labelcolor=text_color)
                
                canvas = FigureCanvasTkAgg(fig, master=plot_window)
                canvas.draw()
                canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
                toolbar = NavigationToolbar2Tk(canvas, plot_window)
                toolbar.update()
                toolbar.pack(side=tk.TOP, fill=tk.X)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to display plot: {e}")

        elif search_mode == 'Eurostat':
            dataset_id = item_values[0]
            try:
                from eurostat import get_data_df
                raw_data = get_data_df(dataset_id)
                def map_country_codes(countries):
                    country_mapping = {
                        'AL': 'Albania', 'AT': 'Austria', 'BE': 'Belgium', 'BG': 'Bulgaria', 'CH': 'Switzerland',
                        'CY': 'Cyprus', 'CZ': 'Czechia', 'DE': 'Germany', 'DK': 'Denmark', 'EE': 'Estonia',
                        'EL': 'Greece', 'ES': 'Spain', 'FI': 'Finland', 'FR': 'France', 'HR': 'Croatia',
                        'HU': 'Hungary', 'IE': 'Ireland', 'IS': 'Iceland', 'IT': 'Italy', 'LT': 'Lithuania',
                        'LU': 'Luxembourg', 'LV': 'Latvia', 'MT': 'Malta', 'NL': 'Netherlands', 'NO': 'Norway',
                        'PL': 'Poland', 'PT': 'Portugal', 'RO': 'Romania', 'SE': 'Sweden', 'SI': 'Slovenia',
                        'SK': 'Slovakia', 'TR': 'Turkey', 'UK': 'United Kingdom', 'EA': 'Euro Area'
                    }
                    mapped_countries = {code: country_mapping.get(code, code) for code in countries}
                    return mapped_countries
                # Wybór kolumn z datami i geo
                date_columns = [col for col in raw_data.columns if col.startswith('geo') or re.match(r'^\d{4}(-Q\d|-M\d{2})?$|^\d{4}-\d{2}$', col)]
                raw_data = raw_data[date_columns]
                raw_data.rename(columns={'geo\\TIME_PERIOD': 'geo'}, inplace=True)

                # Mapowanie skrótów krajów na pełne nazwy
                available_countries = list(raw_data['geo'].unique())
                mapped_countries = map_country_codes(available_countries)  # Użycie funkcji mapującej
                display_countries = list(mapped_countries.values())

                # Okno wyboru krajów
                selected_display_countries = self.choose_countries_dialog(display_countries)

                # Mapowanie wybranych nazw z powrotem na skróty
                selected_countries = [
                    code for code, name in mapped_countries.items() if name in selected_display_countries
                ]

                if not selected_countries:
                    messagebox.showinfo("Info", "No countries selected.")
                    return

                # Filtrowanie danych dla wybranych krajów
                raw_data = raw_data.set_index('geo').T
                raw_data.index = raw_data.index.map(
                    lambda x: pd.to_datetime(f"{x[:4]}-{int(x[-1]) * 3 - 2:02d}-01") if '-Q' in x else (
                        pd.to_datetime(x) if '-' in x else pd.to_datetime(f"{x}-01-01"))
                )
                raw_data.index.name = 'Date'

                filtered_data = raw_data[selected_countries]

                # Rysowanie wykresu
                plot_window = Toplevel(self.root)
                plot_window.title(f"Plot: {dataset_id}")

                # Kolorystyka dostosowana do motywu
                background_color = "#2d2d44"
                axes_color = "#1e1e2f"
                grid_color = "#6366f1"
                text_color = "#ffffff"

                fig, ax = plt.subplots(figsize=(10, 6))
                fig.patch.set_facecolor(background_color)
                ax.set_facecolor(axes_color)

                # Generowanie unikalnych kolorów dla każdego kraju
                from matplotlib import cm
                import numpy as np
                color_map = cm.get_cmap('tab20', len(selected_countries))
                colors = color_map(np.linspace(0, 1, len(selected_countries)))

                for i, country in enumerate(selected_countries):
                    ax.plot(filtered_data.index, filtered_data[country], label=mapped_countries[country], linewidth=2, color=colors[i])

                ax.set_title(f"Dataset: {item_values[1]}", fontsize=14, fontweight="bold", color=text_color)
                ax.set_xlabel("Date", fontsize=12, color=text_color)
                ax.set_ylabel("Value", fontsize=12, color=text_color)
                ax.legend(facecolor=axes_color, edgecolor=grid_color, fontsize=10, labelcolor=text_color)
                ax.grid(True, linestyle="--", linewidth=0.5, color=grid_color)
                ax.tick_params(axis='x', colors=text_color)
                ax.tick_params(axis='y', colors=text_color)

                # Lepsze wyświetlanie dat na osi X
                import matplotlib.dates as mdates
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                fig.autofmt_xdate(rotation=45)

                # Wstawienie wykresu do tkinter
                canvas = FigureCanvasTkAgg(fig, master=plot_window)
                canvas.draw()
                canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

                toolbar = NavigationToolbar2Tk(canvas, plot_window)
                toolbar.update()
                toolbar.pack(side=tk.TOP, fill=tk.X)

            except Exception as e:
                messagebox.showerror("Error", f"Failed to display plot: {e}")

        elif search_mode == 'World Bank':
            indicator_id = item_values[0]
            try:
                # Pobranie danych z Banku Światowego
                url = f'http://api.worldbank.org/v2/country/all/indicator/{indicator_id}'
                params = {
                    'format': 'json',
                    'per_page': 1000,
                    'page': 1
                }

                all_data = []

                # Pobieranie wszystkich stron danych
                while True:
                    response = requests.get(url, params=params)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if len(data) > 1:
                                indicator_data = data[1]
                                all_data.extend(indicator_data)

                                # Sprawdzenie, czy są kolejne strony danych
                                if 'page' in data[0] and data[0]['page'] < data[0]['pages']:
                                    params['page'] += 1
                                else:
                                    break
                            else:
                                break
                        except ValueError:
                            messagebox.showerror("Error", "Failed to decode JSON response.")
                            return
                    else:
                        messagebox.showerror("Error", f"Failed to download data: {response.status_code}")
                        return

                # Tworzenie DataFrame z pełnymi danymi
                df = pd.DataFrame(all_data)

                # Sprawdzenie dostępności danych
                if 'country' in df.columns:
                    df['country_name'] = df['country'].apply(lambda x: x['value'])
                else:
                    messagebox.showerror("Error", "No country data available.")
                    return

                if 'value' not in df.columns or 'date' not in df.columns:
                    messagebox.showerror("Error", "No value or date data available.")
                    return

                # Filtrowanie i przekształcenie danych
                df = df[['country_name', 'date', 'value']].dropna()
                df.rename(columns={'date': 'Date'}, inplace=True)
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')  # Konwersja dat na obiekty datetime
                df = df.dropna(subset=['Date'])  # Usunięcie niepoprawnych dat
                df_pivot = df.pivot(index='Date', columns='country_name', values='value')

                # Sprawdzenie dostępności danych po przekształceniu
                if df_pivot.empty:
                    messagebox.showinfo("Info", "No valid data available to plot.")
                    return

                # Wybór krajów do wyświetlenia
                available_countries = df_pivot.columns.tolist()
                selected_countries = self.choose_countries_dialog(available_countries)

                if selected_countries:
                    # Rysowanie wykresu
                    plot_window = Toplevel(self.root)
                    plot_window.title(f"Plot: {indicator_id}")

                    # Kolorystyka dostosowana do motywu
                    background_color = "#2d2d44"
                    axes_color = "#1e1e2f"
                    grid_color = "#6366f1"
                    text_color = "#ffffff"

                    fig, ax = plt.subplots(figsize=(10, 6))
                    fig.patch.set_facecolor(background_color)
                    ax.set_facecolor(axes_color)

                    # Generowanie unikalnych kolorów dla każdego kraju
                    from matplotlib import cm
                    import numpy as np
                    color_map = cm.get_cmap('tab20', len(selected_countries))
                    colors = color_map(np.linspace(0, 1, len(selected_countries)))

                    for i, country in enumerate(selected_countries):
                        ax.plot(df_pivot.index, df_pivot[country], label=country, linewidth=2, color=colors[i])

                    ax.set_title(f"Indicator: {item_values[1]}", fontsize=14, fontweight="bold", color=text_color)
                    ax.set_xlabel("Date", fontsize=12, color=text_color)
                    ax.set_ylabel("Value", fontsize=12, color=text_color)
                    ax.legend(facecolor=axes_color, edgecolor=grid_color, fontsize=10, labelcolor=text_color)
                    ax.grid(True, linestyle="--", linewidth=0.5, color=grid_color)
                    ax.tick_params(axis='x', colors=text_color)
                    ax.tick_params(axis='y', colors=text_color)

                    # Lepsze wyświetlanie dat na osi X
                    import matplotlib.dates as mdates
                    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                    fig.autofmt_xdate(rotation=45)

                    # Wstawienie wykresu do tkinter
                    canvas = FigureCanvasTkAgg(fig, master=plot_window)
                    canvas.draw()
                    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

                    toolbar = NavigationToolbar2Tk(canvas, plot_window)
                    toolbar.update()
                    toolbar.pack(side=tk.TOP, fill=tk.X)

                else:
                    # Jeśli nie wybrano żadnego kraju, nie pokazujemy błędu, po prostu wychodzimy
                    return

            except Exception as e:
                messagebox.showerror("Error", f"Failed to display plot: {e}")

    def download_eurostat_data(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "No dataset selected.")
            return

        item_data = self.tree.item(selected_item)
        item_values = item_data['values']
        dataset_id = item_values[0]  # Pobierz ID zbioru danych

        try:
            # Pobierz dane z Eurostatu
            raw_data = eurostat.get_data_df(dataset_id)
            if raw_data.empty:
                messagebox.showwarning("Warning", "No data available for the selected dataset.")
                return

            # Zidentyfikuj kolumny dat i geo
            date_columns = [col for col in raw_data.columns if re.match(r'^\d{4}(-Q\d|-M\d{2})?$|^\d{4}-\d{2}$', col)]
            if not date_columns:
                raise ValueError("No valid date columns found in the dataset.")

            if 'geo\\TIME_PERIOD' in raw_data.columns:
                raw_data.rename(columns={'geo\\TIME_PERIOD': 'geo'}, inplace=True)

            if 'geo' not in raw_data.columns:
                raise ValueError("The dataset does not contain a 'geo' column.")

            # Mapowanie skrótów krajów na pełne nazwy
            country_mapping = {
                'AL': 'Albania', 'AT': 'Austria', 'BE': 'Belgium', 'BG': 'Bulgaria', 'CH': 'Switzerland',
                'CY': 'Cyprus', 'CZ': 'Czechia', 'DE': 'Germany', 'DK': 'Denmark', 'EE': 'Estonia',
                'EL': 'Greece', 'ES': 'Spain', 'FI': 'Finland', 'FR': 'France', 'HR': 'Croatia',
                'HU': 'Hungary', 'IE': 'Ireland', 'IS': 'Iceland', 'IT': 'Italy', 'LT': 'Lithuania',
                'LU': 'Luxembourg', 'LV': 'Latvia', 'MT': 'Malta', 'NL': 'Netherlands', 'NO': 'Norway',
                'PL': 'Poland', 'PT': 'Portugal', 'RO': 'Romania', 'SE': 'Sweden', 'SI': 'Slovenia',
                'SK': 'Slovakia', 'TR': 'Turkey', 'UK': 'United Kingdom'
            }
            raw_data['geo'] = raw_data['geo'].map(country_mapping).fillna(raw_data['geo'])

            # Filtrowanie krajów europejskich
            selected_countries = list(country_mapping.values())
            filtered_data = raw_data[raw_data['geo'].isin(selected_countries)]

            if filtered_data.empty:
                messagebox.showwarning("Warning", "No data available for the selected European countries.")
                return

            # Transpozycja tabeli
            filtered_data = filtered_data.set_index('geo').T

            # Przekształcanie indeksu na daty
            def parse_date(date_str):
                try:
                    if '-Q' in date_str:
                        year, quarter = date_str.split('-Q')
                        month = int(quarter) * 3 - 2
                        return pd.Timestamp(f"{year}-{month:02d}-01")
                    elif '-M' in date_str:
                        return pd.Timestamp(f"{date_str}-01")
                    elif re.match(r'^\d{4}-\d{2}$', date_str):
                        return pd.Timestamp(f"{date_str}-01")
                    elif re.match(r'^\d{4}$', date_str):
                        return pd.Timestamp(f"{date_str}-01-01")
                    else:
                        raise ValueError(f"Invalid date format: {date_str}")
                except Exception as e:
                    print(f"Error parsing date '{date_str}': {e}")
                    return None

            filtered_data.index = filtered_data.index.map(parse_date)
            filtered_data = filtered_data.dropna(how='any')  # Usunięcie wierszy z nieprawidłowymi datami
            filtered_data.index.name = 'Date'
            filtered_data.reset_index(inplace=True)

            # Zapis do pliku CSV
            filename = os.path.join(os.getcwd(), f"{dataset_id}_europe.csv")
            filtered_data.to_csv(filename, index=False)
            messagebox.showinfo("Success", f"Dataset saved as {filename}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to download dataset: {e}")

    def show_fundamentals(self):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        item_data = self.tree.item(selected_item)
        item_values = item_data['values']
        symbol = item_values[0]

        try:
            # Fetch fundamental data using yfinance
            ticker = yf.Ticker(symbol)

            # Get company info
            info = ticker.info

            # Get financial statements
            income_statement = ticker.financials
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow

            # Display the fundamental data in a new window
            self.display_fundamental_data(symbol, info, income_statement, balance_sheet, cash_flow)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def display_fundamental_data(self, symbol, info, income_statement, balance_sheet, cash_flow):
        # Create a new window
        fundamentals_window = Toplevel(self.root)
        fundamentals_window.title(f"Fundamentals: {symbol}")

        text_widget = tk.Text(fundamentals_window, wrap='word')
        text_widget.pack(fill='both', expand=True)

        # Display the company info
        text_widget.insert('end', '=== Company Info ===\n')
        for key, value in info.items():
            text_widget.insert('end', f"{key}: {value}\n")

        # Display the income statement
        text_widget.insert('end', '\n=== Income Statement ===\n')
        if not income_statement.empty:
            text_widget.insert('end', income_statement.to_string())
        else:
            text_widget.insert('end', 'No income statement data available.\n')

        # Display the balance sheet
        text_widget.insert('end', '\n=== Balance Sheet ===\n')
        if not balance_sheet.empty:
            text_widget.insert('end', balance_sheet.to_string())
        else:
            text_widget.insert('end', 'No balance sheet data available.\n')

        # Display the cash flow statement
        text_widget.insert('end', '\n=== Cash Flow Statement ===\n')
        if not cash_flow.empty:
            text_widget.insert('end', cash_flow.to_string())
        else:
            text_widget.insert('end', 'No cash flow data available.\n')

        # Make the text widget read-only
        text_widget.config(state='disabled')

    def adjust_column_width(self, ws):
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter  # Pobiera nazwę kolumny
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                    cell.alignment = Alignment(wrap_text=True)  # Zawijanie tekstu w Excelu
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Ustawia maksymalną szerokość kolumny na 50
            ws.column_dimensions[column].width = adjusted_width

    def preprocess_lines(self, lines):
        processed_lines = []
        current_line = ''
        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            if current_line == '':
                current_line = stripped_line
            else:
                # Jeśli linia zaczyna się od liczby lub nie zaczyna się od litery, to kontynuacja
                if re.match(r'^-?\d', stripped_line) or not re.match(r'^[A-Za-z]', stripped_line):
                    current_line += ' ' + stripped_line
                else:
                    # Nowa pozycja
                    processed_lines.append(current_line)
                    current_line = stripped_line
        if current_line:
            processed_lines.append(current_line)
        return processed_lines

    def parse_cash_flow(self, lines):
        headers = []
        data = []
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        lines = self.preprocess_lines(lines)
        for line in lines:
            if not line.strip():
                continue
            # Sprawdzenie, czy linia zawiera nagłówki z datami
            if not headers:
                dates = re.findall(date_pattern, line)
                if dates:
                    tokens = re.split(r'\s{2,}', line.strip())
                    headers = ['Item'] + tokens[1:]  # Pierwsza kolumna to 'Item'
                    continue
            # Parsowanie wierszy danych
            tokens = re.split(r'\s+', line.strip())
            item_tokens = []
            value_tokens = []
            for token in tokens:
                if re.match(r'^-?\d', token) or token == 'NaN':
                    value_tokens.append(token)
                else:
                    item_tokens.append(token)
            item = ' '.join(item_tokens)
            row = [item] + value_tokens
            # Upewnienie się, że liczba kolumn jest zgodna z nagłówkami
            if len(row) < len(headers):
                row += [''] * (len(headers) - len(row))
            elif len(row) > len(headers):
                row = row[:len(headers)]
            data.append(row)
        return headers, data

    def parse_tabular_data(self, lines):
        headers = []
        data = []
        for line in lines:
            # Pomijanie pustych linii
            if not line.strip():
                continue
            # Sprawdzanie, czy linia jest nagłówkiem (sprawdza, czy są daty lub liczby)
            if not headers and re.match(r'.*\d{4}-\d{2}-\d{2}.*', line):
                headers = re.split(r'\s{2,}', line.strip())
                headers = ['Item'] + headers[1:]  # Pierwsza kolumna to 'Item'
            else:
                # Parsowanie wierszy danych
                row = re.split(r'\s{2,}', line.strip())
                # Sprawdzenie, czy pierwsza kolumna zawiera nazwę i wartość
                if len(row) > len(headers):
                    # Przesunięcie wartości do odpowiednich kolumn
                    row = [row[0]] + row[1:len(headers)]
                elif len(row) < len(headers):
                    # Jeśli brakuje wartości, uzupełniamy pustymi ciągami
                    row += [''] * (len(headers) - len(row))
                data.append(row)
        return headers, data

    def parse_data_to_dict(self, data):
        sections = re.split(r'===\s*(.*?)\s*===', data)  # Podział na sekcje po ===
        parsed_data = {}
        for i in range(1, len(sections), 2):
            section_title = sections[i].strip()
            section_data = sections[i + 1].strip()
            parsed_data[section_title] = {}
            lines = section_data.split('\n')

            if section_title in ['Income Statement', 'Balance Sheet', 'Cash Flow Statement']:
                if section_title == 'Cash Flow Statement':
                    headers, data = self.parse_cash_flow(lines)
                else:
                    headers, data = self.parse_tabular_data(lines)
                parsed_data[section_title]['headers'] = headers
                parsed_data[section_title]['data'] = data
            elif ':' in lines[0]:  # Dla sekcji z kluczami i wartościami
                parsed_data[section_title]['headers'] = ['Item', 'Value']
                parsed_data[section_title]['data'] = []
                for line in lines:
                    if ':' in line:
                        key, value = map(str.strip, line.split(':', 1))
                        parsed_data[section_title]['data'].append([key, value])
            else:  # Dla pozostałych tabel
                headers, data = self.parse_tabular_data(lines)
                parsed_data[section_title]['headers'] = headers
                parsed_data[section_title]['data'] = data
        return parsed_data

    def save_to_excel(self, parsed_data, filename):
        wb = Workbook()
        wb.remove(wb.active)  # Usuwamy domyślny arkusz

        for section, data in parsed_data.items():
            sanitized_title = re.sub(r'[\\/*?:[\]]', '', section[:30])  # Nazwa arkusza bez nieprawidłowych znaków
            ws = wb.create_sheet(title=sanitized_title)

            if 'headers' in data and 'data' in data:
                ws.append(data['headers'])  # Dodanie nagłówków
                for row in data['data']:
                    ws.append(row)
                self.adjust_column_width(ws)
            else:
                for key, value in data.items():
                    if key not in ['headers', 'data']:
                        ws.append([key, value])
                self.adjust_column_width(ws)

        wb.save(filename)

    def save_to_pdf(self, parsed_data, filename, company_name):
        # Ustawienie strony w orientacji poziomej A4
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4), leftMargin=2*cm, rightMargin=2*cm)
        elements = []
        styles = getSampleStyleSheet()
        style_heading = styles['Heading1']
        style_body = styles['Normal']

        # Dodanie strony tytułowej
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            alignment=1,  # Wyśrodkowanie
            fontSize=60,
            leading=60,
            textColor=colors.darkblue
        )
        title = f"Financial Report\n{company_name}"
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph(title, title_style))
        elements.append(PageBreak())

        # Definiowanie stylu dla komórek z zawijaniem tekstu
        wrapped_style = ParagraphStyle(
            'Wrapped',
            parent=styles['Normal'],
            alignment=0,
            fontName='Interica',
            fontSize=8,
            leading=10,
            wordWrap='CJK',
        )

        # Styl dla nagłówków tabel
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Normal'],
            alignment=1,
            fontName='Interica-Bold',
            fontSize=10,
            textColor=colors.white
        )

        for section, data in parsed_data.items():
            if data:  # Sprawdzamy, czy sekcja zawiera dane
                elements.append(Paragraph(section, style_heading))
                elements.append(Spacer(1, 0.2*cm))

                if 'headers' in data and 'data' in data:
                    data_table = [data['headers']] + data['data']
                else:
                    data_table = [[k, v] for k, v in data.items() if k not in ['headers', 'data']]

                if data_table:
                    # Konwersja danych do Paragraph z zawijaniem tekstu
                    for i, row in enumerate(data_table):
                        for j, cell in enumerate(row):
                            if i == 0:
                                # Nagłówki tabeli
                                data_table[i][j] = Paragraph(str(cell), header_style)
                            else:
                                data_table[i][j] = Paragraph(str(cell), wrapped_style)

                    # Ustawienie szerokości kolumn proporcjonalnie
                    num_cols = len(data_table[0])
                    max_table_width = doc.width - 4*cm  # Marginesy w tabeli
                    col_width = max_table_width / num_cols
                    col_widths = [col_width for _ in range(num_cols)]

                    t = Table(data_table, colWidths=col_widths, repeatRows=1)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Interica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),  # Profesjonalny kolor tła
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('WORDWRAP', (0, 0), (-1, -1), True),
                    ]))
                    elements.append(t)
                    elements.append(PageBreak())  # Każda sekcja na nowej stronie

        if elements:
            doc.build(elements)
        else:
            messagebox.showinfo("Błąd", "Brak danych do zapisania w pliku PDF.")

    def download_fundamentals(self):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        item_data = self.tree.item(selected_item)
        item_values = item_data['values']
        symbol = item_values[0]

        try:
            # Fetch fundamental data using yfinance
            ticker = yf.Ticker(symbol)

            # Get company info
            info = ticker.info

            # Get financial statements
            income_statement = ticker.financials
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow

            # Prepare parsed_data dictionary directly from DataFrames
            parsed_data = {}

            # Company Info
            parsed_company_info = []
            for k, v in info.items():
                # Spłaszczanie złożonych struktur danych
                if isinstance(v, (dict, list)):
                    v = str(v)
                parsed_company_info.append([k, v])

            parsed_data['Company Info'] = {
                'headers': ['Item', 'Value'],
                'data': parsed_company_info
            }

            # Income Statement
            if not income_statement.empty:
                income_statement.columns = income_statement.columns.strftime('%Y-%m-%d')
                income_statement.index.name = 'Item'
                income_statement.reset_index(inplace=True)
                parsed_data['Income Statement'] = {
                    'headers': income_statement.columns.tolist(),
                    'data': income_statement.values.tolist()
                }

            # Balance Sheet
            if not balance_sheet.empty:
                balance_sheet.columns = balance_sheet.columns.strftime('%Y-%m-%d')
                balance_sheet.index.name = 'Item'
                balance_sheet.reset_index(inplace=True)
                parsed_data['Balance Sheet'] = {
                    'headers': balance_sheet.columns.tolist(),
                    'data': balance_sheet.values.tolist()
                }

            # Cash Flow Statement
            if not cash_flow.empty:
                cash_flow.columns = cash_flow.columns.strftime('%Y-%m-%d')
                cash_flow.index.name = 'Item'
                cash_flow.reset_index(inplace=True)
                parsed_data['Cash Flow Statement'] = {
                    'headers': cash_flow.columns.tolist(),
                    'data': cash_flow.values.tolist()
                }

            # Get company name for filename
            company_name = info.get('longName', symbol)
            company_name = re.sub(r'[\\/*?:"<>|]', '', company_name)

            # Save to Excel and PDF
            self.save_to_excel(parsed_data, f"{company_name}.xlsx")
            self.save_to_pdf(parsed_data, f"{company_name}.pdf", company_name)

            messagebox.showinfo("Success", f"Fundamentals saved as {company_name}.xlsx and {company_name}.pdf")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while downloading fundamentals: {e}")
    
    def choose_countries_dialog(self, countries):
        dialog_window = Toplevel(self.root)
        dialog_window.title("Select Countries")

        # Ustawienia okna (rozmiar i centrowanie)
        dialog_width = 450
        dialog_height = 500
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (dialog_width // 2)
        y = (screen_height // 2) - (dialog_height // 2)
        dialog_window.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        dialog_window.configure(bg="#2d2d44")

        # Ustawienia przewijalnego obszaru
        canvas = tk.Canvas(dialog_window, bg="#2d2d44", highlightthickness=0)
        scrollbar_y = tk.Scrollbar(dialog_window, orient="vertical", command=canvas.yview, bg="#2d2d44")
        scrollable_frame = tk.Frame(canvas, bg="#2d2d44")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_y.set)

        # Obsługa scrolla myszy
        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

        dialog_window.bind_all("<MouseWheel>", _on_mousewheel)

        # Pakowanie elementów w oknie
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")

        # Lista zmiennych i checkboxów do zaznaczenia krajów
        country_vars = {}
        max_columns = 2
        for idx, country in enumerate(countries):
            var = tk.IntVar(value=0)
            checkbox = tk.Checkbutton(scrollable_frame, text=country, variable=var, bg="#2d2d44", fg="#ffffff",
                                    selectcolor="#3c3c58", activebackground="#2d2d44", activeforeground="#ffffff",
                                    font=("Inter", 10), anchor="w")
            row = idx // max_columns
            col = idx % max_columns
            checkbox.grid(row=row, column=col, sticky='w', padx=10, pady=5)
            country_vars[country] = var

        # Funkcja zatwierdzająca wybór krajów
        def on_submit():
            selected_countries = [country for country, var in country_vars.items() if var.get() == 1]
            dialog_window.destroy()
            self.selected_countries = selected_countries

        # Przyciski
        button_frame = tk.Frame(dialog_window, bg="#2d2d44")
        button_frame.pack(side="bottom", pady=10, fill="x")

        submit_button = tk.Button(button_frame, text="Submit", command=on_submit,
                                bg="#4caf50", fg="#ffffff", font=("Inter", 12, "bold"),
                                activebackground="#388e3c", activeforeground="#ffffff", relief="flat")
        submit_button.pack(side="top", pady=10)

        self.selected_countries = []
        self.root.wait_window(dialog_window)
        return self.selected_countries

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                global fred_api, fmp_api_key
                fred_api = settings.get("FRED_API_KEY", None)
                fmp_api_key = settings.get("FMP_API_KEY", None)

                # Załaduj ulubione z walidacją
                favorites_data = settings.get("favorites", [])
                if favorites_data:
                    # Sprawdzanie, czy dane mają wymagane kolumny
                    self.favorites = pd.DataFrame(favorites_data)
                    required_columns = ['id', 'title', 'frequency', 'source']
                    for col in required_columns:
                        if col not in self.favorites.columns:
                            self.favorites[col] = ''  # Dodanie brakujących kolumn z pustymi wartościami
                    self.update_favorites_tree()
                else:
                    self.favorites = pd.DataFrame(columns=['id', 'title', 'frequency', 'source'])

        except FileNotFoundError:
            # Jeśli plik ustawień nie istnieje, ustaw wartości domyślne
            fred_api = None
            fmp_api_key = None
            self.favorites = pd.DataFrame(columns=['id', 'title', 'frequency', 'source'])
        except Exception as e:
            # Obsługa błędów, jeśli dane są uszkodzone
            messagebox.showerror("Error", f"Failed to load settings: {e}")
            self.favorites = pd.DataFrame(columns=['id', 'title', 'frequency', 'source'])

    def save_settings(self):
        settings = {
            "FRED_API_KEY": fred_api,
            "FMP_API_KEY": fmp_api_key,
            "favorites": self.favorites.to_dict(orient='records'),  # Zapisanie ulubionych jako listy słowników
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)

    def api_login_prompt(self):
        # API Login Dialog
        login_window = Toplevel(self.root)
        login_window.title("API Keys Login")
        login_window.geometry("450x300")  # Adjust size for the login window
        login_window.configure(bg="#1e1e2f")  # Match the background color to the theme
        login_window.grab_set()  # Prevent interaction with the main window until closed
        login_window.attributes("-topmost", True)  # Keep the login window on top

        # Center the window on the screen
        login_window.update_idletasks()
        x = (login_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (login_window.winfo_screenheight() // 2) - (350 // 2)
        login_window.geometry(f"+{x}+{y}")

        frame = tk.Frame(login_window, bg="#1e1e2f", padx=20, pady=20)
        frame.pack(expand=True, fill=tk.BOTH)

        # FRED API Key input
        tk.Label(frame, text="Enter FRED API Key:", font=("Inter", 12), bg="#1e1e2f", fg="#ffffff").pack(pady=5, anchor='w')
        fred_api_var = tk.StringVar()
        fred_api_entry = tk.Entry(frame, textvariable=fred_api_var, font=("Inter", 12), bg="#2d2d44", fg="#ffffff",
                                insertbackground="#ffffff", relief="flat")
        fred_api_entry.pack(fill='x', pady=5)

        # Button to open link to get FRED API Key
        def open_fred_link():
            import webbrowser
            webbrowser.open("https://fred.stlouisfed.org/docs/api/fred/")

        tk.Button(frame, text="Get FRED API Key", command=open_fred_link, font=("Inter", 10, "bold"),
                bg="#3c3c58", fg="#ffffff", activebackground="#45455a", activeforeground="#ffffff", relief="flat").pack(pady=5, anchor='w')

        # FMP API Key input
        tk.Label(frame, text="Enter FMP API Key:", font=("Inter", 12), bg="#1e1e2f", fg="#ffffff").pack(pady=5, anchor='w')
        fmp_api_var = tk.StringVar()
        fmp_api_entry = tk.Entry(frame, textvariable=fmp_api_var, font=("Inter", 12), bg="#2d2d44", fg="#ffffff",
                                insertbackground="#ffffff", relief="flat")
        fmp_api_entry.pack(fill='x', pady=5)

        # Button to open link to get FMP API Key
        def open_fmp_link():
            import webbrowser
            webbrowser.open("https://financialmodelingprep.com/developer")

        tk.Button(frame, text="Get FMP API Key", command=open_fmp_link, font=("Inter", 10, "bold"),
                bg="#3c3c58", fg="#ffffff", activebackground="#45455a", activeforeground="#ffffff", relief="flat").pack(pady=5, anchor='w')

        # Verify and Save button
        def verify_keys():
            global fred_api, fmp_api_key
            fred_api = fred_api_var.get().strip()
            fmp_api_key = fmp_api_var.get().strip()

            if not fred_api or not fmp_api_key:
                self.show_error("Both API keys are required!", login_window)
                return

            # Verify FRED API Key
            fred_valid = False
            try:
                response = requests.get(f"https://api.stlouisfed.org/fred/series?series_id=GNPCA&api_key={fred_api}&file_type=json")
                if response.status_code == 200:
                    fred_valid = True
                else:
                    self.show_error("Invalid FRED API Key.", login_window)
                    return
            except requests.RequestException as e:
                self.show_error(f"Failed to verify FRED API Key: {e}", login_window)
                return

            # Verify FMP API Key
            fmp_valid = False
            try:
                response = requests.get(f"https://financialmodelingprep.com/api/v3/profile/AAPL?apikey={fmp_api_key}")
                if response.status_code == 200:
                    fmp_valid = True
                else:
                    self.show_error("Invalid FMP API Key.", login_window)
                    return
            except requests.RequestException as e:
                self.show_error(f"Failed to verify FMP API Key: {e}", login_window)
                return

            if fred_valid and fmp_valid:
                self.save_settings()
                login_window.destroy()

        tk.Button(frame, text="Verify and Save", command=verify_keys, font=("Inter", 12, "bold"),
                bg="#2d2d44", fg="#ffffff", activebackground="#3c3c58", activeforeground="#ffffff", relief="flat").pack(pady=15)

        self.root.wait_window(login_window)

    def show_error(self, message, parent=None):
        """Display an error message box with updated theme."""
        error_window = Toplevel(parent or self.root)
        error_window.title("Error")
        error_window.geometry("300x150")
        error_window.configure(bg="#1e1e2f")
        error_window.attributes("-topmost", True)

        tk.Label(error_window, text=message, font=("Inter", 12), bg="#1e1e2f", fg="#ffffff", wraplength=250).pack(pady=20)
        tk.Button(error_window, text="Close", command=error_window.destroy, font=("Inter", 10, "bold"),
                bg="#2d2d44", fg="#ffffff", activebackground="#3c3c58", activeforeground="#ffffff", relief="flat").pack(pady=10)

        # Center the error window
        error_window.update_idletasks()
        x = (error_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (error_window.winfo_screenheight() // 2) - (150 // 2)
        error_window.geometry(f"+{x}+{y}")

    def on_close(self):
        self.save_settings()
        self.root.destroy()
# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    
    app = DataSearchApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
