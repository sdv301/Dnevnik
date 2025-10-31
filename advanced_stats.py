import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

class TradingAdvancedStatistics:
    def __init__(self, excel_file):
        self.excel_file = excel_file
    
    def generate_trading_report(self):
        """Генерация детального торгового отчета"""
        try:
            df = pd.read_excel(self.excel_file)
            
            if df.empty:
                return "📊 Нет торговых данных для отчета"
            
            # Основная статистика
            total_trades = len(df)
            profitable_trades = len(df[df['profit_pips'] > 0])
            losing_trades = len(df[df['profit_pips'] < 0])
            total_profit = df['profit_pips'].sum()
            avg_profit = df['profit_pips'].mean()
            
            # Статистика по символам
            symbol_stats = df.groupby('symbol').agg({
                'profit_pips': ['count', 'sum', 'mean'],
                'volume': 'sum'
            }).round(2)
            
            # Статистика по типам операций
            operation_stats = df.groupby('operation_type').agg({
                'profit_pips': ['count', 'sum', 'mean']
            }).round(2)
            
            # Создание отчета
            report = "📊 ДЕТАЛЬНЫЙ ТОРГОВЫЙ ОТЧЕТ\n\n"
            report += f"📈 Всего сделок: {total_trades}\n"
            report += f"✅ Прибыльных: {profitable_trades}\n"
            report += f"❌ Убыточных: {losing_trades}\n"
            report += f"💰 Общий профит: {total_profit:.1f} пипсов\n"
            report += f"📊 Средний профит: {avg_profit:.1f} пипсов\n"
            report += f"💹 Эффективность: {(profitable_trades/total_trades*100):.1f}%\n\n"
            
            # Статистика по символам
            report += "💱 СТАТИСТИКА ПО СИМВОЛАМ:\n"
            for symbol in symbol_stats.index:
                stats = symbol_stats.loc[symbol]
                count = stats[('profit_pips', 'count')]
                total = stats[('profit_pips', 'sum')]
                avg = stats[('profit_pips', 'mean')]
                volume = stats[('volume', 'sum')]
                
                report += f"\n{symbol}:\n"
                report += f"   📊 Сделок: {count}\n"
                report += f"   💰 Общий профит: {total:.1f} пипсов\n"
                report += f"   📈 Средний профит: {avg:.1f} пипсов\n"
                report += f"   📦 Общий объем: {volume} лотов\n"
            
            # Статистика по типам операций
            report += "\n🔄 СТАТИСТИКА ПО ОПЕРАЦИЯМ:\n"
            for op_type in operation_stats.index:
                stats = operation_stats.loc[op_type]
                count = stats[('profit_pips', 'count')]
                total = stats[('profit_pips', 'sum')]
                avg = stats[('profit_pips', 'mean')]
                
                report += f"\n{op_type}:\n"
                report += f"   📊 Сделок: {count}\n"
                report += f"   💰 Общий профит: {total:.1f} пипсов\n"
                report += f"   📈 Средний профит: {avg:.1f} пипсов\n"
            
            return report
            
        except Exception as e:
            return f"❌ Ошибка при генерации отчета: {e}"

    def get_user_trading_stats(self, user_id):
        """Получение торговой статистики конкретного пользователя"""
        try:
            df = pd.read_excel(self.excel_file)
            
            if df.empty:
                return "📊 Нет торговых данных о пользователе"
            
            user_data = df[df['user_id'] == user_id]
            
            if user_data.empty:
                return "📊 Данные пользователя не найдены"
            
            total_trades = len(user_data)
            profitable_trades = len(user_data[user_data['profit_pips'] > 0])
            total_profit = user_data['profit_pips'].sum()
            avg_profit = user_data['profit_pips'].mean()
            
            # Лучшая и худшая сделки
            best_trade = user_data.loc[user_data['profit_pips'].idxmax()]
            worst_trade = user_data.loc[user_data['profit_pips'].idxmin()]
            
            progress_report = f"""
📊 ВАША ТОРГОВАЯ СТАТИСТИКА:

📈 Всего сделок: {total_trades}
✅ Прибыльных: {profitable_trades}
❌ Убыточных: {total_trades - profitable_trades}

💰 Общий профит: {total_profit:.1f} пипсов
📊 Средний профит: {avg_profit:.1f} пипсов
💹 Эффективность: {(profitable_trades/total_trades*100):.1f}%

🏆 Лучшая сделка:
   Символ: {best_trade['symbol']}
   Профит: {best_trade['profit_pips']} пипсов

📉 Худшая сделка:
   Символ: {worst_trade['symbol']}
   Профит: {worst_trade['profit_pips']} пипсов
            """
            
            return progress_report
            
        except Exception as e:
            return f"❌ Ошибка при получении статистики: {e}"