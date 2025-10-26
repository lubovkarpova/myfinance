"""
Модуль для работы с Google Sheets API
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json


class GoogleSheetsManager:
    def __init__(self, credentials_file, spreadsheet_name):
        """
        Инициализация менеджера Google Sheets
        
        Args:
            credentials_file: путь к JSON файлу с credentials
            spreadsheet_name: название таблицы в Google Sheets
        """
        self.credentials_file = credentials_file
        self.spreadsheet_name = spreadsheet_name
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        
    def connect(self):
        """Подключение к Google Sheets"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Проверяем, есть ли JSON в переменной окружения (для Railway)
            google_creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            
            if google_creds_json:
                # Используем credentials из переменной окружения
                creds_dict = json.loads(google_creds_json)
                credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                    creds_dict, scope
                )
            else:
                # Используем файл (для локальной разработки)
                credentials = ServiceAccountCredentials.from_json_keyfile_name(
                    self.credentials_file, scope
                )
            
            self.client = gspread.authorize(credentials)
            
            # Открываем или создаем таблицу
            try:
                self.spreadsheet = self.client.open(self.spreadsheet_name)
            except gspread.SpreadsheetNotFound:
                self.spreadsheet = self.client.create(self.spreadsheet_name)
                # Делаем таблицу доступной для редактирования
                self.spreadsheet.share('', perm_type='anyone', role='writer')
            
            # Открываем или создаем первый лист
            try:
                self.worksheet = self.spreadsheet.sheet1
            except:
                self.worksheet = self.spreadsheet.add_worksheet(title="Транзакции", rows="1000", cols="10")
            
            # Проверяем и создаем заголовки если их нет
            self._ensure_headers()
            
            return True
            
        except Exception as e:
            print(f"Ошибка подключения к Google Sheets: {e}")
            return False
    
    def _ensure_headers(self):
        """Создает заголовки в таблице, если их нет"""
        try:
            first_row = self.worksheet.row_values(1)
            
            # Если таблица пустая - создаем все заголовки
            if not first_row or len(first_row) == 0:
                headers = [
                    'Date ',
                    'Type',
                    'Description',
                    'Category',
                    'Amount ',
                    '',
                    'Amount in ILS',
                    'User ',
                    'input',
                    'Subscription '
                ]
                self.worksheet.update('A1:J1', [headers])
                # Форматируем заголовки
                self.worksheet.format('A1:J1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                })
                print("[INFO] Headers created with 'input' column")
            
            # Проверяем, есть ли колонка 'input'
            elif len(first_row) < 9 or first_row[8] != 'input':
                print(f"[WARNING] Table has {len(first_row)} columns, expected 9")
                print(f"[WARNING] Current headers: {first_row}")
                print("[INFO] Please add 'input' column manually or recreate the table")
                
        except Exception as e:
            print(f"Ошибка при создании заголовков: {e}")
    
    def add_transaction(self, transaction_data):
        """
        Добавляет транзакцию в таблицу
        
        Args:
            transaction_data: словарь с данными транзакции
                - date: дата (DD/MM/YY)
                - type: тип (Income/Expense)
                - description: описание
                - category: категория
                - amount: сумма
                - currency: валюта
                - amount_ils: сумма в шекелях
                - username: имя пользователя
        """
        try:
            # Форматируем данные для корректного отображения в Google Sheets
            row = [
                str(transaction_data.get('date', '')),  # Дата как текст
                transaction_data.get('type', ''),
                transaction_data.get('description', ''),
                transaction_data.get('category', ''),
                transaction_data.get('amount', ''),  # Число
                '',  # Пустая колонка 6
                transaction_data.get('amount_ils', ''),  # Число
                transaction_data.get('username', ''),
                transaction_data.get('input', ''),  # Оригинальный текст
                transaction_data.get('subscription', '')  # Информация о подписке
            ]
            
            # Логируем для отладки
            print(f"[DEBUG] Adding row: {row}")
            print(f"[DEBUG] Input value: '{transaction_data.get('input', 'EMPTY')}'")
            
            # Используем value_input_option='RAW' чтобы данные записывались как есть, без интерпретации
            self.worksheet.append_row(row, value_input_option='RAW')
            return True
            
        except Exception as e:
            print(f"Ошибка при добавлении транзакции: {e}")
            return False
    
    def add_transactions_batch(self, transactions):
        """
        Добавляет несколько транзакций за раз
        
        Args:
            transactions: список словарей с данными транзакций
        """
        try:
            rows = []
            for transaction in transactions:
                # Форматируем данные для корректного отображения в Google Sheets
                row = [
                    str(transaction.get('date', '')),  # Дата как текст
                    transaction.get('type', ''),
                    transaction.get('description', ''),
                    transaction.get('category', ''),
                    transaction.get('amount', ''),  # Число
                    '',  # Пустая колонка 6
                    transaction.get('amount_ils', ''),  # Число
                    transaction.get('username', ''),
                    transaction.get('input', ''),  # Оригинальный текст
                    transaction.get('subscription', '')  # Информация о подписке
                ]
                rows.append(row)
            
            if rows:
                # Используем value_input_option='RAW' чтобы данные записывались как есть, без интерпретации
                self.worksheet.append_rows(rows, value_input_option='RAW')
                return True
            
            return False
            
        except Exception as e:
            print(f"Ошибка при добавлении транзакций: {e}")
            return False
    
    def get_spreadsheet_url(self):
        """Возвращает URL таблицы"""
        if self.spreadsheet:
            return self.spreadsheet.url
        return None

