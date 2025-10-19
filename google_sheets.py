"""
Модуль для работы с Google Sheets API
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os


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
            if not first_row or len(first_row) == 0:
                headers = [
                    'Date',
                    'Type',
                    'Description',
                    'Category',
                    'Amount',
                    'Currency',
                    'Amount in ILS',
                    'User',
                    'User ID'
                ]
                self.worksheet.update('A1:I1', [headers])
                # Форматируем заголовки
                self.worksheet.format('A1:I1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                })
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
                - user_id: ID пользователя
        """
        try:
            row = [
                transaction_data.get('date', ''),
                transaction_data.get('type', ''),
                transaction_data.get('description', ''),
                transaction_data.get('category', ''),
                transaction_data.get('amount', ''),
                transaction_data.get('currency', ''),
                transaction_data.get('amount_ils', ''),
                transaction_data.get('username', ''),
                transaction_data.get('user_id', '')
            ]
            
            self.worksheet.append_row(row)
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
                row = [
                    transaction.get('date', ''),
                    transaction.get('type', ''),
                    transaction.get('description', ''),
                    transaction.get('category', ''),
                    transaction.get('amount', ''),
                    transaction.get('currency', ''),
                    transaction.get('amount_ils', ''),
                    transaction.get('username', ''),
                    transaction.get('user_id', '')
                ]
                rows.append(row)
            
            if rows:
                self.worksheet.append_rows(rows)
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

