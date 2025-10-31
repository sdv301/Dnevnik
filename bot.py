import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import cv2
import pytesseract
import pandas as pd
from PIL import Image
import io
import re
from datetime import datetime

# Настройка пути к Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
EXCEL_FILE = "trading_results.xlsx"
BOT_TOKEN = "7870831167:AAEfFVkPa4bavSwdg-8wwZxuh6X9IRX0Mfs"  # ЗАМЕНИТЕ НА ВАШ ТОКЕН!

class TradingDataProcessor:
    def __init__(self, excel_file):
        self.excel_file = excel_file
        self._init_excel_file()
    
    def _init_excel_file(self):
        """Инициализация Excel файла с колонками для торговых данных"""
        if not os.path.exists(self.excel_file):
            df = pd.DataFrame(columns=[
                'date_processed', 'user_id', 'username',
                'symbol', 'operation_type', 'volume',
                'entry_price', 'exit_price', 'profit_currency',
                'profit_percent', 'sl_price', 'tp_price',
                'swap', 'commission', 'order_id',
                'entry_time', 'exit_time', 'raw_text'
            ])
            df.to_excel(self.excel_file, index=False)
            print(f"✅ Создан новый Excel файл для торговых данных: {self.excel_file}")
    
    def extract_trading_data_from_image(self, image_path):
        """Извлечение торговых данных из изображения с помощью Tesseract OCR"""
        try:
            print(f"🔍 Обрабатываю торговый скриншот: {image_path}")
            
            # Загрузка изображения
            img = cv2.imread(image_path)
            if img is None:
                print("❌ Не удалось загрузить изображение")
                return None
            
            # Преобразование в grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Улучшение качества изображения для OCR
            gray = cv2.medianBlur(gray, 3)
            gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Извлечение текста с английским языком (для торговых терминов)
            print("📖 Распознаю текст с помощью Tesseract...")
            text = pytesseract.image_to_string(gray, lang='eng')
            print(f"✅ Текст распознан: {len(text)} символов")
            
            # Парсинг торговых данных
            trading_data = self._parse_trading_data(text)
            
            return {
                'raw_text': text,
                'trading_data': trading_data,
                'clean_text': self._clean_text(text)
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки изображения: {e}")
            return None
    
    def _parse_trading_data(self, text):
        """Парсинг конкретных торговых данных из текста"""
        data = {
            'symbol': '',
            'operation_type': '', 
            'volume': 0,
            'entry_price': 0,
            'exit_price': 0,
            'profit_currency': 0,  # Прибыль в валюте
            'profit_pips': 0,
            'profit_percent': 0,
            'sl_price': 0,
            'tp_price': 0,
            'swap': 0,
            'commission': 0,
            'order_id': '',
            'entry_time': '',
            'exit_time': ''
        }
        
        try:
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                line_clean = line.strip()
                
                # Поиск прибыли в валюте (число с плавающей точкой, может быть отрицательным)
                if data['profit_currency'] == 0:
                    # Ищем паттерн для денежной прибыли: может быть с знаками валют или просто число
                    currency_profit_match = re.search(r'[-]?\d+\.?\d*\s*\$|[-]?\d+\.?\d*\s*USD|[-]?\d+\.?\d*\s*€|[-]?\d+\.?\d*\s*EUR', line_clean)
                    if currency_profit_match:
                        # Извлекаем только числовую часть
                        profit_value = re.search(r'[-]?\d+\.?\d*', currency_profit_match.group())
                        if profit_value:
                            data['profit_currency'] = float(profit_value.group())
                    else:
                        # Альтернативный поиск: число в конце строки или в середине
                        numbers_in_line = re.findall(r'[-]?\d+\.?\d*', line_clean)
                        if len(numbers_in_line) >= 3:  # Если в строке несколько чисел
                            # Берем последнее число как потенциальную прибыль
                            potential_profit = numbers_in_line[-1]
                            try:
                                profit_val = float(potential_profit)
                                # Фильтруем разумные значения прибыли (не цены, не объемы)
                                if -1000 <= profit_val <= 1000 and profit_val != 0:
                                    data['profit_currency'] = profit_val
                            except:
                                pass
                        
                # Поиск символа (EURUSD, GBPUSD и т.д.)
                if not data['symbol']:
                    symbol_match = re.search(r'\b([A-Z]{6})\b', line_clean)
                    if symbol_match:
                        data['symbol'] = symbol_match.group(1)
                
                # Поиск типа операции (Sell/Buy)
                if not data['operation_type']:
                    if 'Sell' in line_clean or 'sell' in line_clean:
                        data['operation_type'] = 'Sell'
                    elif 'Buy' in line_clean or 'buy' in line_clean:
                        data['operation_type'] = 'Buy'
                
                # Поиск объема
                if data['volume'] == 0:
                    volume_match = re.search(r'\b(\d+)\s*(lot|лот)?\b', line_clean, re.IGNORECASE)
                    if volume_match:
                        data['volume'] = float(volume_match.group(1))
                
                # Поиск цен входа и выхода
                price_pattern = r'\d+\.\d{5}'
                prices = re.findall(price_pattern, line_clean)
                
                if len(prices) >= 2:
                    if data['entry_price'] == 0:
                        data['entry_price'] = float(prices[0])
                    if data['exit_price'] == 0:
                        data['exit_price'] = float(prices[1])
                
                # Поиск SL и TP
                if 'S/L:' in line_clean or 'SL:' in line_clean:
                    sl_prices = re.findall(price_pattern, line_clean)
                    if sl_prices:
                        data['sl_price'] = float(sl_prices[0])
                
                if 'T/P:' in line_clean or 'TP:' in line_clean:
                    tp_prices = re.findall(price_pattern, line_clean)
                    if tp_prices:
                        data['tp_price'] = float(tp_prices[0])
                
                # Поиск свопа и комиссии
                if 'Своп:' in line_clean or 'Swap:' in line_clean:
                    swap_match = re.search(r'[-]?\d+\.?\d*', line_clean)
                    if swap_match:
                        data['swap'] = float(swap_match.group())
                
                if 'Комиссия:' in line_clean or 'Commission:' in line_clean:
                    commission_match = re.search(r'[-]?\d+\.?\d*', line_clean)
                    if commission_match:
                        data['commission'] = float(commission_match.group())
                
                # Поиск ID ордера
                if not data['order_id']:
                    order_match = re.search(r'#(\d+)', line_clean)
                    if order_match:
                        data['order_id'] = order_match.group(1)
                
                # Поиск времени
                time_pattern = r'\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}'
                times = re.findall(time_pattern, line_clean)
                if len(times) >= 2:
                    data['entry_time'] = times[0]
                    data['exit_time'] = times[1]
                elif len(times) == 1 and not data['entry_time']:
                    data['entry_time'] = times[0]
            
            # Расчет профита в пипсах
            if data['entry_price'] > 0 and data['exit_price'] > 0:
                if data['operation_type'] == 'Sell':
                    data['profit_pips'] = round((data['entry_price'] - data['exit_price']) * 10000, 1)
                else:  # Buy
                    data['profit_pips'] = round((data['exit_price'] - data['entry_price']) * 10000, 1)
                
                # Расчет профита в процентах
                data['profit_percent'] = round((data['profit_pips'] / data['entry_price'] * 10000) * 100, 4)
            
            print(f"📊 Извлеченные торговые данные: {data}")
            return data
            
        except Exception as e:
            print(f"❌ Ошибка парсинга торговых данных: {e}")
            return data
    
    def _clean_text(self, text):
        """Очистка текста от лишних символов"""
        text = ' '.join(text.split())
        return text[:1000]
    
    def save_to_excel(self, data, user_info):
        """Сохранение торговых данных в Excel"""
        try:
            df = pd.read_excel(self.excel_file)
            
            trading_data = data['trading_data']
            
            # Создание новой записи
            new_row = {
                'date_processed': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': user_info['id'],
                'username': user_info.get('username', 'Unknown'),
                'symbol': trading_data['symbol'],
                'operation_type': trading_data['operation_type'],
                'volume': trading_data['volume'],
                'entry_price': trading_data['entry_price'],
                'exit_price': trading_data['exit_price'],
                'profit_currency': trading_data['profit_currency'],  # ДОБАВЬ ЭТУ СТРОЧКУ
                'profit_pips': trading_data['profit_pips'],
                'profit_percent': trading_data['profit_percent'],
                'sl_price': trading_data['sl_price'],
                'tp_price': trading_data['tp_price'],
                'swap': trading_data['swap'],
                'commission': trading_data['commission'],
                'order_id': trading_data['order_id'],
                'entry_time': trading_data['entry_time'],
                'exit_time': trading_data['exit_time'],
                'raw_text': data['clean_text']
            }
            
            # Добавление новой строки
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_excel(self.excel_file, index=False)
            print(f"✅ Торговые данные сохранены в Excel. Всего записей: {len(df)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в Excel: {e}")
            return False

# Инициализация процессора данных
processor = TradingDataProcessor(EXCEL_FILE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """
🤖 Добро пожаловать в бот для анализа торговых скриншотов!

📸 Отправьте мне скриншот торговой операции, и я:
• Извлеку торговые данные с помощью Tesseract OCR
• Распознаю символ, тип операции, цены, SL/TP
• Сохраню всё в Excel таблицу

📊 Команды:
/start - начать работу
/statistics - статистика операций
/help - помощь

💡 Примеры скриншотов:
• Результаты сделок Forex
• Скриншоты из торговых платформ
• Ордера с ценами входа/выхода
    """
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📖 Доступные команды:

/start - начать работу
/statistics - статистика торговых операций
/help - эта справка

📸 Как использовать:
1. Сделайте скриншот торговой операции
2. Отправьте скриншот боту как изображение
3. Бот автоматически извлечет данные и сохранит в Excel

💡 Поддерживаемые данные:
• Валютная пара (EURUSD, GBPUSD и т.д.)
• Тип операции (Buy/Sell)
• Объем (лоты)
• Цены входа и выхода
• Stop Loss и Take Profit
• Своп и комиссия
• Время операции
    """
    await update.message.reply_text(help_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик получения фото"""
    try:
        processing_msg = await update.message.reply_text("🔄 Обрабатываю торговый скриншот...")
        
        # Получение фото
        photo_file = await update.message.photo[-1].get_file()
        temp_file = f"temp_trade_{update.message.message_id}.jpg"
        await photo_file.download_to_drive(temp_file)
        
        # Извлечение данных
        extracted_data = processor.extract_trading_data_from_image(temp_file)
        
        if not extracted_data:
            await processing_msg.edit_text("❌ Не удалось обработать скриншот. Убедитесь, что изображение четкое и содержит торговые данные.")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return
        
        # Сохранение в Excel
        user = update.message.from_user
        user_info = {'id': user.id, 'username': user.username or user.first_name}
        success = processor.save_to_excel(extracted_data, user_info)
        
        # Формирование ответа
        if success:
            td = extracted_data['trading_data']
            response = f"""
✅ Торговые данные успешно сохранены!

📊 Извлеченная информация:
• Символ: {td['symbol'] or 'Не найден'}
• Операция: {td['operation_type'] or 'Не найден'}
• Объем: {td['volume'] or 'Не найден'} лот(ов)
• Цена входа: {td['entry_price'] or 'Не найден'}
• Цена выхода: {td['exit_price'] or 'Не найден'}
• Прибыль: {td['profit_currency'] or '0'} USD

💾 Данные сохранены в Excel таблицу.
Используйте /statistics для просмотра статистики.
            """
        else:
            response = "❌ Ошибка при сохранении данных в Excel."
        
        await processing_msg.edit_text(response)
        
        # Очистка
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_photo: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке скриншота.")

async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /statistics - статистика операций"""
    try:
        df = pd.read_excel(EXCEL_FILE)
        
        if df.empty:
            await update.message.reply_text("📊 Пока нет торговых данных для анализа.")
            return
        
        # Статистика операций
        total_operations = len(df)
        profitable_operations = len(df[df['profit_currency'] > 0])
        total_profit_currency = df['profit_currency'].sum()
        avg_profit_per_trade = df['profit_currency'].mean()
        
        response = f"""
📊 СТАТИСТИКА ТОРГОВЫХ ОПЕРАЦИЙ:

📈 Всего операций: {total_operations}
✅ Прибыльных: {profitable_operations}
📉 Убыточных: {total_operations - profitable_operations}

💰 Общий профит: {total_profit_currency:.2f} USD
📊 Средний профит за сделку: {avg_profit_per_trade:.2f} USD

💹 Эффективность: {(profitable_operations/total_operations*100):.1f}%
        """
        await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в statistics: {e}")
        await update.message.reply_text("❌ Ошибка при получении статистики.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"❌ Exception while handling an update: {context.error}")
    try:
        await update.message.reply_text("❌ Произошла непредвиденная ошибка.")
    except:
        pass

def main():
    """Основная функция"""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ЗАМЕНИТЕ BOT_TOKEN НА ВАШ ТОКЕН!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавление обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("statistics", statistics))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_error_handler(error_handler)
    
    print("🤖 Бот для анализа торговых скриншотов запущен!")
    print("📍 Tesseract готов к работе!")
    print("📊 Excel файл: trading_results.xlsx")
    application.run_polling()

if __name__ == '__main__':
    main()