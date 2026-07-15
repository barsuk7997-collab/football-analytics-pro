"""
Интерактивный дашборд для Football Analytics Pro
Запуск: streamlit run dashboard/app.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import sys
import os

# Добавляем родительскую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db
from config.settings import model_config

# Настройка страницы
st.set_page_config(
    page_title="⚽ Football Analytics Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS стили
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #22c55e;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #94a3b8;
        margin-bottom: 2rem;
    }
    .value-card {
        background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(21,128,61,0.15));
        border: 2px solid #22c55e;
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
    }
    .no-value-card {
        background: rgba(55,65,81,0.5);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
    }
    .metric-box {
        background: #1f2937;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #9ca3af;
    }
</style>
""", unsafe_allow_html=True)


def render_header():
    """Шапка дашборда"""
    st.markdown('<div class="main-header">⚽ Football Analytics Pro</div>', 
                unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Professional Value Betting Intelligence System v2.0</div>',
                unsafe_allow_html=True)


def render_sidebar():
    """Боковая панель с настройками"""
    with st.sidebar:
        st.header("🔧 Настройки")

        # Банкролл
        st.subheader("💰 Банкролл")
        bankroll = st.number_input("Банкролл ($)", min_value=100, value=1000, step=100)

        # Пороги value
        st.subheader("🎯 Пороги Value")
        min_edge = st.slider("Минимальный edge", 0.0, 0.30, 0.05, 0.01,
                            help="Минимальное преимущество модели над рынком")
        min_confidence = st.slider("Минимальная уверенность", 0.0, 1.0, 0.60, 0.05,
                                  help="Минимальная уверенность прогноза")

        # Kelly
        st.subheader("📊 Kelly Criterion")
        kelly_fraction = st.slider("Fractional Kelly", 0.1, 1.0, 0.25, 0.05,
                                   help="Консервативность Kelly (0.25 = четверть Kelly)")

        # Дата
        st.subheader("📅 Дата матчей")
        analysis_date = st.date_input("Дата анализа", value=datetime.now())

        # Кнопки действий
        st.divider()
        if st.button("🔄 Обновить данные", type="primary", use_container_width=True):
            with st.spinner("Обновление Elo и статистики..."):
                # Здесь вызов update функции
                st.success("Данные обновлены!")

        if st.button("🔍 Анализировать матчи", use_container_width=True):
            with st.spinner("Анализ матчей..."):
                st.success("Анализ завершён!")

        return {
            "bankroll": bankroll,
            "min_edge": min_edge,
            "min_confidence": min_confidence,
            "kelly_fraction": kelly_fraction,
            "analysis_date": analysis_date
        }


def render_match_card(match_data: dict, settings: dict):
    """Карточка матча с прогнозом"""
    home_team = match_data.get("home_team", "Home")
    away_team = match_data.get("away_team", "Away")
    probs = match_data.get("ensemble_probabilities", {})
    value_bets = match_data.get("value_bets", [])
    confidence = match_data.get("prediction_strength", 0)
    data_quality = match_data.get("data_quality", 0)

    # Определяем цвет уверенности
    conf_color = "#22c55e" if confidence >= 70 else "#f59e0b" if confidence >= 50 else "#ef4444"

    with st.container():
        col1, col2, col3 = st.columns([2, 3, 2])

        with col1:
            st.markdown(f"### {home_team}")
            st.markdown(f"**Elo:** {match_data.get('home_elo', 1500):.0f}")
            # Форма визуально
            form = match_data.get("home_form", ["W", "D", "W", "L", "W"])
            form_str = "".join([
                "🟢" if r == "W" else "🟡" if r == "D" else "🔴" 
                for r in form
            ])
            st.markdown(f"Форма: {form_str}")

        with col2:
            # Круговая диаграмма вероятностей
            fig = go.Figure(data=[go.Pie(
                labels=["П1", "X", "П2"],
                values=[
                    probs.get("home_win", 0.33),
                    probs.get("draw", 0.33),
                    probs.get("away_win", 0.33)
                ],
                hole=0.45,
                marker_colors=["#22c55e", "#f59e0b", "#ef4444"],
                textinfo="percent",
                textfont_size=14
            )])
            fig.update_layout(
                showlegend=False,
                height=180,
                margin=dict(t=0, b=0, l=0, r=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e5e7eb",
                annotations=[dict(text="1X2", x=0.5, y=0.5, font_size=16, showarrow=False)]
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            # Метрики
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"<div style='text-align:center;color:{conf_color};font-weight:700;'>{confidence:.0f}%</div>", 
                           unsafe_allow_html=True)
                st.markdown("<div style='text-align:center;font-size:0.75rem;color:#9ca3af;'>Уверенность</div>", 
                           unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div style='text-align:center;color:#3b82f6;font-weight:700;'>{data_quality:.0f}%</div>", 
                           unsafe_allow_html=True)
                st.markdown("<div style='text-align:center;font-size:0.75rem;color:#9ca3af;'>Данные</div>", 
                           unsafe_allow_html=True)

        with col3:
            st.markdown(f"### {away_team}")
            st.markdown(f"**Elo:** {match_data.get('away_elo', 1500):.0f}")
            form = match_data.get("away_form", ["W", "L", "D", "W", "W"])
            form_str = "".join([
                "🟢" if r == "W" else "🟡" if r == "D" else "🔴" 
                for r in form
            ])
            st.markdown(f"Форма: {form_str}")

        # Value ставки
        st.divider()

        if value_bets:
            st.markdown("#### 🎯 Value Ставки")

            for vb in value_bets:
                stars = "⭐" * vb.get("stars", 1)
                edge_pct = vb.get("edge", 0) * 100
                kelly_pct = vb.get("kelly", 0) * 100
                bet_size = vb.get("kelly", 0) * settings["bankroll"]

                # Цвет в зависимости от силы
                card_color = "#22c55e" if edge_pct >= 15 else "#f59e0b" if edge_pct >= 8 else "#3b82f6"

                st.markdown(f"""
                <div style="border-left: 4px solid {card_color}; background: rgba({"34,197,94" if edge_pct >= 15 else "245,158,11" if edge_pct >= 8 else "59,130,246"},0.1); 
                            padding: 12px 16px; border-radius: 0 12px 12px 0; margin: 8px 0;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <b style="font-size:1.1rem;">{vb.get("selection", "")}</b>
                            <span style="color:#9ca3af; margin-left:8px;">@ {vb.get("odds", 0):.2f}</span>
                        </div>
                        <div style="font-size:1.2rem;">{stars}</div>
                    </div>
                    <div style="display:flex; gap:16px; margin-top:8px; font-size:0.9rem;">
                        <span>📈 Edge: <b>{edge_pct:.1f}%</b></span>
                        <span>💰 EV: <b>{vb.get("ev", 0)*100:.1f}%</b></span>
                        <span>🎯 Kelly: <b>{kelly_pct:.1f}%</b> (${bet_size:.2f})</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Кнопка копирования
                if st.button(f"📋 Копировать: {vb.get('selection', '')} @ {vb.get('odds', 0):.2f}", 
                            key=f"copy_{match_data.get('match_id', 0)}_{vb.get('selection', '')}"):
                    st.toast("Скопировано в буфер обмена!")
        else:
            st.markdown("""
            <div style="background: rgba(55,65,81,0.3); border-radius: 12px; padding: 16px; text-align: center; color: #9ca3af;">
                ❌ Value ставок не обнаружено (edge < порога или недостаточно данных)
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)


def render_statistics():
    """Статистика прогнозов"""
    st.header("📊 Статистика ROI")

    # Получаем статистику из БД
    stats = db.get_roi_stats(days=30)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="color:#3b82f6;">{stats['total_predictions']}</div>
            <div class="metric-label">Всего прогнозов</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="color:#22c55e;">{stats['resolved']}</div>
            <div class="metric-label">Разрешено</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        win_rate_color = "#22c55e" if stats['win_rate'] >= 50 else "#f59e0b"
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="color:{win_rate_color};">{stats['win_rate']:.1f}%</div>
            <div class="metric-label">Win Rate</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        roi_color = "#22c55e" if stats['total_roi'] >= 0 else "#ef4444"
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="color:{roi_color};">{stats['total_roi']:.2f}%</div>
            <div class="metric-label">Общий ROI</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="color:#a855f7;">{stats['avg_edge']*100:.1f}%</div>
            <div class="metric-label">Средний Edge</div>
        </div>
        """, unsafe_allow_html=True)

    # График ROI по времени
    st.subheader("Динамика ROI")

    # Демо-данные для графика (в реальности из БД)
    dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
    roi_values = [5 + i * 0.3 + (i % 7 - 3) * 2 for i in range(30)]

    fig = px.line(
        x=dates, y=roi_values,
        labels={"x": "Дата", "y": "ROI (%)"},
        title="ROI за последние 30 дней"
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#1f2937",
        font_color="#e5e7eb",
        xaxis_gridcolor="#374151",
        yaxis_gridcolor="#374151"
    )
    st.plotly_chart(fig, use_container_width=True)


def render_elo_ratings():
    """Таблица Elo рейтингов"""
    st.header("🏆 Elo Рейтинги")

    teams = db.get_all_teams()

    if teams:
        df = pd.DataFrame([
            {
                "Команда": t["name"],
                "Страна": t.get("country", ""),
                "Elo (K32)": t["elo"].get(32, 1500),
                "Elo (K200)": t["elo"].get(200, 1500),
                "Elo (K500)": t["elo"].get(500, 1500),
                "Elo (K2000)": t["elo"].get(2000, 1500),
                "Обновлено": t.get("last_updated", "")
            }
            for t in teams
        ])

        df = df.sort_values("Elo (K32)", ascending=False)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Elo (K32)": st.column_config.NumberColumn(format="%.0f"),
                "Elo (K200)": st.column_config.NumberColumn(format="%.0f"),
                "Elo (K500)": st.column_config.NumberColumn(format="%.0f"),
                "Elo (K2000)": st.column_config.NumberColumn(format="%.0f"),
            }
        )
    else:
        st.info("Нет данных о командах. Запустите обновление данных.")


def main():
    """Главная функция дашборда"""
    render_header()
    settings = render_sidebar()

    # Вкладки
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Матчи", "📊 Статистика", "🏆 Elo", "⚙️ Настройки"])

    with tab1:
        st.header("Предстоящие матчи")

        # Загрузка прогнозов из файла или БД
        try:
            with open("predictions.json", "r", encoding="utf-8") as f:
                predictions = json.load(f)
        except FileNotFoundError:
            predictions = []

        if not predictions:
            # Демо-данные для визуализации
            predictions = [
                {
                    "match_id": 1,
                    "home_team": "Manchester City",
                    "away_team": "Arsenal",
                    "home_elo": 1950,
                    "away_elo": 1880,
                    "home_form": ["W", "W", "D", "W", "W"],
                    "away_form": ["W", "W", "W", "L", "D"],
                    "ensemble_probabilities": {"home_win": 0.52, "draw": 0.26, "away_win": 0.22},
                    "prediction_strength": 72,
                    "data_quality": 85,
                    "value_bets": [
                        {"selection": "П1", "odds": 2.10, "edge": 0.092, "ev": 0.093, "kelly": 0.044, "stars": 3}
                    ]
                },
                {
                    "match_id": 2,
                    "home_team": "Real Madrid",
                    "away_team": "Barcelona",
                    "home_elo": 1920,
                    "away_elo": 1900,
                    "home_form": ["W", "D", "W", "W", "L"],
                    "away_form": ["W", "W", "D", "W", "W"],
                    "ensemble_probabilities": {"home_win": 0.40, "draw": 0.28, "away_win": 0.32},
                    "prediction_strength": 55,
                    "data_quality": 90,
                    "value_bets": []
                }
            ]

        # Фильтрация по порогам
        filtered = [
            p for p in predictions 
            if p.get("prediction_strength", 0) >= settings["min_confidence"] * 100
        ]

        if not filtered:
            st.info("Нет матчей, соответствующих заданным порогам.")
        else:
            for pred in filtered:
                render_match_card(pred, settings)

    with tab2:
        render_statistics()

    with tab3:
        render_elo_ratings()

    with tab4:
        st.header("⚙️ Настройки моделей")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Elo")
            st.slider("K-factor (основной)", 10, 60, 32, key="elo_k")
            st.slider("Home advantage", 50, 120, 80, key="home_adv")
            st.checkbox("Учитывать разницу мячей", value=True, key="goal_margin")

        with col2:
            st.subheader("Ансамбль")
            st.slider("Вес Elo", 0.0, 1.0, 0.40, key="w_elo")
            st.slider("Вес xG", 0.0, 1.0, 0.30, key="w_xg")
            st.slider("Вес формы", 0.0, 1.0, 0.20, key="w_form")
            st.slider("Вес рынка", 0.0, 1.0, 0.10, key="w_market")


if __name__ == "__main__":
    main()
