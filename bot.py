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
EXCEL_FILE = "data_results.xlsx"
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # ЗАМЕНИТЕ НА ВАШ ТОКЕН!

class DataProcessor:
    def __init__(self, excel_file):
        self.excel_file = excel_file
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
            
            # Сохранение обработанного изображения для отладки
            processed_path = "processed_" + os.path.basename(image_path)
            cv2.imwrite(processed_path, gray)
            print(f"✅ Обработанное изображение сохранено: {processed_path}")
            
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
        return text[:500]  # Ограничиваем длину для Excel
    
    def _is_likely_score(self, number_str):
        """Проверяет, похоже ли число на оценку/балл"""
        try:
            num = float(number_str)
            return 0 <= num <= 100
        except:
            return False
    
    def save_to_excel(self, data, user_info):
        """Сохранение данных в Excel"""
        try:
            # Чтение существующего файла
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
            
            # Сохранение
            df.to_excel(self.excel_file, index=False)
            print(f"✅ Данные сохранены в Excel. Всего записей: {len(df)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в Excel: {e}")
            return False
    
    def get_statistics(self):
        """Получение статистики из Excel файла"""
        try:
            df = pd.read_excel(self.excel_file)
            
            if df.empty:
                return "📊 Пока нет данных для анализа."
            
            # Статистика по всем записям
            total_records = len(df)
            
            # Лучшие и худшие результаты из колонок
            best_scores = df['best_score'].dropna()
            worst_scores = df['worst_score'].dropna()
            avg_scores = df['average_score'].dropna()
            
            if best_scores.empty:
                return "📊 Не найдено подходящих оценок для анализа."
            
            overall_best = best_scores.max()
            overall_worst = worst_scores.min() if not worst_scores.empty else 0
            overall_avg = avg_scores.mean() if not avg_scores.empty else 0
            
            # Статистика по пользователям
            user_stats = df.groupby('username').agg({
                'best_score': 'max',
                'worst_score': 'min', 
                'average_score': 'mean',
                'user_id': 'count'
            }).round(2)
            
            # Формирование ответа
            response = f"""
📊 ОБЩАЯ СТАТИСТИКА:

📈 Всего записей: {total_records}
👥 Уникальных пользователей: {len(user_stats)}

🏆 ЛУЧШИЕ РЕЗУЛЬТАТЫ:
• Лучший результат: {overall_best}
• Худший результат: {overall_worst}
• Средний результат: {overall_avg:.2f}

👤 ПОЛЬЗОВАТЕЛИ:
"""
            # Добавляем статистику по каждому пользователю
            for username, stats in user_stats.iterrows():
                response += f"\n{username}:"
                response += f"\n  🏆 Лучший: {stats['best_score']}"
                response += f"\n  📉 Худший: {stats['worst_score']}"
                response += f"\n  📊 Средний: {stats['average_score']:.2f}"
                response += f"\n  📝 Записей: {stats['user_id']}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета статистики: {e}")
            return f"❌ Ошибка при расчете статистики: {e}"

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
/statistics - посмотреть статистику
/help - помощь

🎯 Примеры скриншотов:
• Результаты тестов
• Таблицы с оценками
• Любые изображения с текстом и числами
    """
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📖 Доступные команды:

/start - начать работу
/statistics - посмотреть статистику результатов
/help - эта справка

📸 Как использовать:
1. Сделайте скриншот (например, с оценками, результатами тестов)
2. Отправьте скриншот боту как изображение
3. Бот автоматически обработает изображение и сохранит данные

💡 Советы:
• Изображение должно быть четким
• Текст должен быть хорошо читаем
• Для лучших результатов используйте скриншоты вместо фотографий
    """
    await update.message.reply_text(help_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик получения фото"""
    try:
        # Отправка сообщения о начале обработки
        processing_msg = await update.message.reply_text("🔄 Обрабатываю изображение...")
        
        # Получение фото (берем самое качественное)
        photo_file = await update.message.photo[-1].get_file()
        
        # Сохранение временного файла
        temp_file = f"temp_photo_{update.message.message_id}.jpg"
        await photo_file.download_to_drive(temp_file)
        
        print(f"📥 Изображение сохранено: {temp_file}")
        
        # Извлечение данных с помощью Tesseract
        extracted_data = processor.extract_data_from_image(temp_file)
        
        if not extracted_data:
            await processing_msg.edit_text("❌ Не удалось обработать изображение. Убедитесь, что изображение четкое и содержит текст.")
            # Очистка временного файла
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return
        
        # Подготовка информации о пользователе
        user = update.message.from_user
        user_info = {
            'id': user.id,
            'username': user.username or user.first_name
        }
        
        # Сохранение в Excel
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

📝 Текст: 
{extracted_data['clean_text'][:150] + '...' if len(extracted_data['clean_text']) > 150 else extracted_data['clean_text']}

💾 Данные сохранены в Excel таблицу.
Используйте /statistics для просмотра статистики.
            """
        else:
            response = "❌ Ошибка при сохранении данных в Excel."
        
        await processing_msg.edit_text(response)
        
        # Очистка временных файлов
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        # Удаление обработанного изображения если оно существует
        processed_file = "processed_temp_photo_" + str(update.message.message_id) + ".jpg"
        if os.path.exists(processed_file):
            os.remove(processed_file)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_photo: {e}")
        try:
            await update.message.reply_text("❌ Произошла ошибка при обработке изображения.")
        except:
            pass

async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /statistics"""
    try:
        await update.message.reply_text("📊 Считаю статистику...")
        
        stats = processor.get_statistics()
        await update.message.reply_text(stats)
            
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
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("statistics", statistics))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    print("🤖 Бот запущен...")
    print("📍 Tesseract готов к работе!")
    print("📊 Excel файл: data_results.xlsx")
    application.run_polling()

if __name__ == '__main__':
    main()