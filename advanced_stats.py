import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os

class AdvancedStatistics:
    def __init__(self, excel_file):
        self.excel_file = excel_file
    
    def generate_detailed_report(self):
        """Генерация детального отчета"""
        try:
            df = pd.read_excel(self.excel_file)
            
            if df.empty:
                return "📊 Нет данных для отчета"
            
            # Анализ данных
            all_scores = []
            user_stats = {}
            
            for _, row in df.iterrows():
                user_id = row['user_id']
                username = row['username']
                
                try:
                    scores = eval(row['scores'])
                    if isinstance(scores, list) and scores:
                        if user_id not in user_stats:
                            user_stats[user_id] = {
                                'username': username,
                                'scores': [],
                                'count': 0
                            }
                        
                        user_stats[user_id]['scores'].extend(scores)
                        user_stats[user_id]['count'] += 1
                        all_scores.extend(scores)
                except:
                    continue
            
            if not all_scores:
                return "📊 Не найдено оценок для анализа"
            
            # Создание отчета
            report = "📊 ДЕТАЛЬНЫЙ ОТЧЕТ\n\n"
            report += f"📈 Всего оценок: {len(all_scores)}\n"
            report += f"👥 Пользователей: {len(user_stats)}\n"
            report += f"🏆 Лучший результат: {max(all_scores):.1f}\n"
            report += f"📉 Худший результат: {min(all_scores):.1f}\n"
            report += f"📊 Средний результат: {sum(all_scores)/len(all_scores):.1f}\n\n"
            
            # Статистика по пользователям
            report += "👤 РЕЙТИНГ ПОЛЬЗОВАТЕЛЕЙ:\n"
            user_best_scores = []
            
            for user_id, data in user_stats.items():
                if data['scores']:
                    best_score = max(data['scores'])
                    worst_score = min(data['scores'])
                    avg_score = sum(data['scores']) / len(data['scores'])
                    user_best_scores.append((data['username'], best_score, avg_score, worst_score, len(data['scores'])))
            
            # Сортировка по лучшему результату
            user_best_scores.sort(key=lambda x: x[1], reverse=True)
            
            for i, (username, best, avg, worst, count) in enumerate(user_best_scores[:10], 1):
                report += f"{i}. {username}:\n"
                report += f"   🏆 Лучший: {best:.1f}\n"
                report += f"   📊 Средний: {avg:.1f}\n"
                report += f"   📉 Худший: {worst:.1f}\n"
                report += f"   📝 Записей: {count}\n\n"
            
            return report
            
        except Exception as e:
            return f"❌ Ошибка при генерации отчета: {e}"

    def create_score_distribution_chart(self):
        """Создание графика распределения оценок"""
        try:
            df = pd.read_excel(self.excel_file)
            
            if df.empty:
                return None
            
            # Сбор всех оценок
            all_scores = []
            for _, row in df.iterrows():
                try:
                    scores = eval(row['scores'])
                    if isinstance(scores, list):
                        all_scores.extend(scores)
                except:
                    continue
            
            if not all_scores:
                return None
            
            # Создание графика
            plt.figure(figsize=(10, 6))
            
            # Гистограмма распределения оценок
            plt.hist(all_scores, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            plt.xlabel('Оценки')
            plt.ylabel('Количество')
            plt.title('Распределение оценок')
            plt.grid(True, alpha=0.3)
            
            # Сохранение графика
            chart_path = "score_distribution.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_path
            
        except Exception as e:
            print(f"❌ Ошибка создания графика: {e}")
            return None

    def get_user_progress(self, user_id):
        """Получение прогресса конкретного пользователя"""
        try:
            df = pd.read_excel(self.excel_file)
            
            if df.empty:
                return "📊 Нет данных о пользователе"
            
            user_data = df[df['user_id'] == user_id]
            
            if user_data.empty:
                return "📊 Данные пользователя не найдены"
            
            all_scores = []
            dates = []
            
            for _, row in user_data.iterrows():
                try:
                    scores = eval(row['scores'])
                    if isinstance(scores, list) and scores:
                        all_scores.extend(scores)
                        dates.append(row['date'])
                except:
                    continue
            
            if not all_scores:
                return "📊 Не найдено оценок пользователя"
            
            best_score = max(all_scores)
            worst_score = min(all_scores)
            avg_score = sum(all_scores) / len(all_scores)
            total_records = len(user_data)
            
            progress_report = f"""
📊 ВАША СТАТИСТИКА:

🏆 Лучший результат: {best_score:.1f}
📉 Худший результат: {worst_score:.1f}
📊 Средний результат: {avg_score:.1f}
📝 Всего записей: {total_records}
🎯 Всего оценок: {len(all_scores)}

📈 Прогресс: {'📈' if len(all_scores) > 1 and all_scores[-1] >= avg_score else '📉'}
            """
            
            return progress_report
            
        except Exception as e:
            return f"❌ Ошибка при получении статистики: {e}"