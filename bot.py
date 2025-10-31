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
from advanced_stats import AdvancedStatistics  # Импортируем наш класс

# Настройка пути к Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
EXCEL_FILE = "data_results.xlsx"
BOT_TOKEN = "7870831167:AAEfFVkPa4bavSwdg-8wwZxuh6X9IRX0Mfs"  # ЗАМЕНИТЕ НА ВАШ ТОКЕН!

class DataProcessor:
    def __init__(self, excel_file):
        self.excel_file = excel_file
        self.advanced_stats = AdvancedStatistics(excel_file)  # Создаем экземпляр
        self._init_excel_file()
    
    def _init_excel_file(self):
        """Инициализация Excel файла с нужными колонками"""
        if not os.path.exists(self.excel_file):
            df = pd.DataFrame(columns=[
                'date', 'user_id', 'username', 
                'numbers', 'scores', 'text_data',
                'best_score', 'worst_score', 'average_score'
            ])
            df.to_excel(self.excel_file, index=False)
            print(f"✅ Создан новый Excel файл: {self.excel_file}")
    
    def extract_data_from_image(self, image_path):
        """Извлечение данных из изображения с помощью Tesseract OCR"""
        try:
            print(f"🔍 Обрабатываю изображение: {image_path}")
            
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
            
            # Извлечение текста с русским и английским языками
            print("📖 Распознаю текст с помощью Tesseract...")
            text = pytesseract.image_to_string(gray, lang='rus+eng')
            print(f"✅ Текст распознан: {len(text)} символов")
            
            # Поиск чисел в тексте
            numbers = re.findall(r'\d+\.?\d*', text)
            print(f"🔢 Найдено чисел: {numbers}")
            
            # Поиск оценок/баллов
            scores = []
            for num in numbers:
                try:
                    score = float(num)
                    if 0 <= score <= 100:  # Предполагаем, что оценки от 0 до 100
                        scores.append(score)
                except:
                    continue
            
            print(f"🎯 Найдено оценок: {scores}")
            
            return {
                'text': text,
                'numbers': numbers,
                'scores': scores,
                'clean_text': self._clean_text(text)
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки изображения: {e}")
            return None
    
    def _clean_text(self, text):
        """Очистка текста от лишних символов"""
        text = ' '.join(text.split())
        return text[:500]
    
    def save_to_excel(self, data, user_info):
        """Сохранение данных в Excel"""
        try:
            df = pd.read_excel(self.excel_file)
            
            # Расчет статистики для этой записи
            scores = data['scores']
            best_score = max(scores) if scores else 0
            worst_score = min(scores) if scores else 0
            average_score = sum(scores) / len(scores) if scores else 0
            
            # Создание новой записи
            new_row = {
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': user_info['id'],
                'username': user_info.get('username', 'Unknown'),
                'numbers': str(data['numbers']),
                'scores': str(data['scores']),
                'text_data': data['clean_text'],
                'best_score': best_score,
                'worst_score': worst_score,
                'average_score': round(average_score, 2)
            }
            
            # Добавление новой строки
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_excel(self.excel_file, index=False)
            print(f"✅ Данные сохранены в Excel. Всего записей: {len(df)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в Excel: {e}")
            return False

# Инициализация процессора данных
processor = DataProcessor(EXCEL_FILE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """
🤖 Добро пожаловать в бот для анализа скриншотов!

📸 Отправьте мне скриншот, и я:
• Извлеку текст с изображения с помощью Tesseract OCR
• Найду числа и оценки
• Сохраню всё в Excel таблицу

📊 Команды:
/start - начать работу
/statistics - общая статистика
/detailed_stats - детальная статистика
/my_stats - моя статистика
/help - помощь
    """
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📖 Доступные команды:

/start - начать работу
/statistics - общая статистика
/detailed_stats - детальная статистика с рейтингом
/my_stats - персональная статистика
/help - эта справка

📸 Как использовать:
1. Сделайте скриншот (например, с оценками, результатами тестов)
2. Отправьте скриншот боту как изображение
3. Бот автоматически обработает изображение и сохранит данные
    """
    await update.message.reply_text(help_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик получения фото"""
    try:
        processing_msg = await update.message.reply_text("🔄 Обрабатываю изображение...")
        
        # Получение фото
        photo_file = await update.message.photo[-1].get_file()
        temp_file = f"temp_photo_{update.message.message_id}.jpg"
        await photo_file.download_to_drive(temp_file)
        
        # Извлечение данных
        extracted_data = processor.extract_data_from_image(temp_file)
        
        if not extracted_data:
            await processing_msg.edit_text("❌ Не удалось обработать изображение.")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return
        
        # Сохранение в Excel
        user = update.message.from_user
        user_info = {'id': user.id, 'username': user.username or user.first_name}
        success = processor.save_to_excel(extracted_data, user_info)
        
        # Формирование ответа
        if success:
            scores_text = ", ".join(map(str, extracted_data['scores'])) if extracted_data['scores'] else "не найдено"
            response = f"""
✅ Данные успешно сохранены!

📊 Извлеченная информация:
• Найдено чисел: {len(extracted_data['numbers'])}
• Найдено оценок: {len(extracted_data['scores'])}
• Оценки: {scores_text}

💾 Используйте /my_stats для просмотра вашей статистики.
            """
        else:
            response = "❌ Ошибка при сохранении данных."
        
        await processing_msg.edit_text(response)
        
        # Очистка
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_photo: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке изображения.")

async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /statistics - общая статистика"""
    try:
        df = pd.read_excel(EXCEL_FILE)
        
        if df.empty:
            await update.message.reply_text("📊 Пока нет данных для анализа.")
            return
        
        # Простая статистика
        total_records = len(df)
        best_scores = df['best_score'].dropna()
        
        if best_scores.empty:
            await update.message.reply_text("📊 Не найдено оценок для анализа.")
            return
        
        response = f"""
📊 ОБЩАЯ СТАТИСТИКА:

📈 Всего записей: {total_records}
🏆 Лучший результат: {best_scores.max():.1f}
📉 Худший результат: {df['worst_score'].min():.1f}
📊 Средний результат: {df['average_score'].mean():.1f}

Для детальной статистики используйте /detailed_stats
        """
        await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в statistics: {e}")
        await update.message.reply_text("❌ Ошибка при получении статистики.")

async def detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /detailed_stats - детальная статистика"""
    try:
        await update.message.reply_text("📊 Формирую детальный отчет...")
        
        # Используем AdvancedStatistics для детального отчета
        report = processor.advanced_stats.generate_detailed_report()
        await update.message.reply_text(report)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в detailed_stats: {e}")
        await update.message.reply_text("❌ Ошибка при генерации детального отчета.")

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /my_stats - персональная статистика"""
    try:
        user = update.message.from_user
        await update.message.reply_text("📊 Формирую вашу статистику...")
        
        # Используем AdvancedStatistics для персональной статистики
        user_stats = processor.advanced_stats.get_user_progress(user.id)
        await update.message.reply_text(user_stats)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в my_stats: {e}")
        await update.message.reply_text("❌ Ошибка при получении вашей статистики.")

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
    application.add_handler(CommandHandler("detailed_stats", detailed_stats))
    application.add_handler(CommandHandler("my_stats", my_stats))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_error_handler(error_handler)
    
    print("🤖 Бот запущен с расширенной статистикой!")
    print("📍 Tesseract готов к работе!")
    application.run_polling()

if __name__ == '__main__':
    main()