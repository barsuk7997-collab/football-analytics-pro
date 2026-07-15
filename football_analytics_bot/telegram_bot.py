"""
Telegram бот для отправки уведомлений о value-ставках
Запуск: python telegram_bot.py
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config.settings import api_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FootballTelegramBot:
    """
    Telegram бот для Football Analytics Pro

    Команды:
    /start - Приветствие и статус
    /today - Анализ сегодняшних матчей
    /value - Только value-ставки
    /stats - ROI статистика
    /elo - Топ команд по Elo
    /help - Справка
    """

    def __init__(self):
        self.token = api_config.TELEGRAM_BOT_TOKEN
        self.chat_id = api_config.TELEGRAM_CHAT_ID
        self.bot = Bot(token=self.token)
        self.enabled = api_config.TELEGRAM_ENABLED

    async def send_prediction(self, prediction: Dict):
        """Отправить прогноз в Telegram"""
        if not self.enabled:
            return

        msg = self._format_prediction(prediction)
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error("Failed to send prediction: %s", e)

    async def send_value_alert(self, prediction: Dict, value_bets: List[Dict]):
        """Отправить срочное уведомление о сильной value-ставке"""
        if not self.enabled or not value_bets:
            return

        # Фильтруем только сильные ставки
        strong = [vb for vb in value_bets if vb.get("stars", 0) >= 4]
        if not strong:
            return

        home = prediction.get("home_team", "Home")
        away = prediction.get("away_team", "Away")
        confidence = prediction.get("prediction_strength", 0)

        lines = []
        lines.append("🚨 <b>СИЛЬНАЯ VALUE СТАВКА!</b>")
        lines.append("")
        lines.append("⚽ " + home + " vs " + away)
        lines.append("📊 Уверенность: " + str(round(confidence, 0)) + "%")
        lines.append("")

        for vb in strong:
            selection = vb.get("selection", "")
            odds = vb.get("odds", 0)
            edge = vb.get("edge", 0) * 100
            kelly = vb.get("kelly", 0) * 100
            ev = vb.get("ev", 0) * 100

            lines.append("🎯 <b>" + selection + "</b>")
            lines.append("   Кэф: " + str(round(odds, 2)) + " | Edge: " + str(round(edge, 1)) + "%")
            lines.append("   Kelly: " + str(round(kelly, 1)) + "% банка")
            lines.append("   EV: " + str(round(ev, 1)) + "%")
            lines.append("")

        lines.append("⏰ Не упустите момент!")

        msg = "\n".join(lines)

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error("Failed to send alert: %s", e)

    async def send_daily_summary(self, predictions: List[Dict]):
        """Отправить ежедневную сводку"""
        if not self.enabled:
            return

        total = len(predictions)
        value_count = sum(1 for p in predictions if p.get("value_bets"))
        strong_count = sum(
            1 for p in predictions 
            for vb in p.get("value_bets", []) 
            if vb.get("stars", 0) >= 4
        )

        lines = []
        lines.append("📅 <b>Ежедневная сводка</b>")
        lines.append("")
        lines.append("📊 Всего матчей: " + str(total))
        lines.append("💎 Value найдено: " + str(value_count))
        lines.append("🚨 Сильных ставок: " + str(strong_count))
        lines.append("")

        if value_count > 0:
            lines.append("<b>Лучшие ставки дня:</b>")
            for p in predictions:
                vbs = p.get("value_bets", [])
                if vbs:
                    best = max(vbs, key=lambda x: x.get("edge", 0))
                    lines.append("⚽ " + p.get("home_team", "") + " vs " + p.get("away_team", ""))
                    lines.append("   " + best.get("selection", "") + " @ " + str(round(best.get("odds", 0), 2)) + " (edge " + str(round(best.get("edge", 0)*100, 1)) + "%)")

        msg = "\n".join(lines)

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error("Failed to send summary: %s", e)

    async def send_roi_stats(self, stats: Dict):
        """Отправить статистику ROI"""
        if not self.enabled:
            return

        lines = []
        lines.append("📈 <b>Статистика ROI (30 дней)</b>")
        lines.append("")
        lines.append("📊 Всего прогнозов: " + str(stats.get("total_predictions", 0)))
        lines.append("✅ Разрешено: " + str(stats.get("resolved", 0)))
        lines.append("🏆 Побед: " + str(stats.get("wins", 0)) + " | ❌ Поражений: " + str(stats.get("losses", 0)))
        lines.append("📉 Win Rate: " + str(round(stats.get("win_rate", 0), 1)) + "%")
        lines.append("💰 Общий ROI: " + str(round(stats.get("total_roi", 0), 2)) + "%")
        lines.append("📊 Средний Edge: " + str(round(stats.get("avg_edge", 0)*100, 2)) + "%")
        lines.append("🎯 Yield: " + str(round(stats.get("yield_percent", 0), 2)) + "%")

        msg = "\n".join(lines)

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error("Failed to send stats: %s", e)

    def _format_prediction(self, pred: Dict) -> str:
        """Форматировать прогноз для Telegram"""
        probs = pred.get("ensemble_probabilities", {})
        home = pred.get("home_team", "Home")
        away = pred.get("away_team", "Away")
        confidence = pred.get("prediction_strength", 0)
        data_quality = pred.get("data_quality", 0)

        lines = []
        lines.append("⚽ <b>" + home + "</b> vs <b>" + away + "</b>")
        lines.append("")
        lines.append("📊 Вероятности:")
        lines.append("   П1: " + str(round(probs.get("home_win", 0)*100, 1)) + "%")
        lines.append("   X:  " + str(round(probs.get("draw", 0)*100, 1)) + "%")
        lines.append("   П2: " + str(round(probs.get("away_win", 0)*100, 1)) + "%")
        lines.append("")
        lines.append("🎯 Уверенность: " + str(round(confidence, 0)) + "%")
        lines.append("📈 Качество данных: " + str(round(data_quality, 0)) + "%")
        lines.append("")

        vbs = pred.get("value_bets", [])
        if vbs:
            lines.append("💎 <b>Value ставки:</b>")
            for vb in vbs:
                stars = "⭐" * vb.get("stars", 1)
                lines.append("   " + vb.get("selection", "") + " @ " + str(round(vb.get("odds", 0), 2)) + " (edge " + str(round(vb.get("edge", 0)*100, 1)) + "%) " + stars)
        else:
            lines.append("❌ Value ставок не обнаружено")

        return "\n".join(lines)

    # === Command Handlers ===
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /start"""
        lines = [
            "⚽ <b>Football Analytics Pro</b>",
            "",
            "Профессиональный аналитический модуль для value betting.",
            "",
            "<b>Команды:</b>",
            "/today - Анализ сегодняшних матчей",
            "/value - Только value-ставки",
            "/stats - ROI статистика",
            "/elo - Топ по Elo",
            "/help - Справка"
        ]
        msg = "\n".join(lines)
        await update.message.reply_text(msg, parse_mode="HTML")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /help"""
        lines = [
            "<b>Справка по командам:</b>",
            "",
            "/start - Запуск бота",
            "/today - Полный анализ матчей на сегодня",
            "/value - Только матчи с value-ставками",
            "/stats - Статистика ROI за 30 дней",
            "/elo [league_id] - Топ-10 команд по Elo",
            "/help - Эта справка",
            "",
            "Бот автоматически отправляет уведомления о сильных value-ставках."
        ]
        msg = "\n".join(lines)
        await update.message.reply_text(msg, parse_mode="HTML")

    def run(self):
        """Запустить бота (блокирующий вызов)"""
        if not self.enabled:
            logger.warning("Telegram bot is disabled")
            return

        application = Application.builder().token(self.token).build()

        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))

        logger.info("Telegram bot started")
        application.run_polling()


# Синглтон
telegram_bot = FootballTelegramBot()
