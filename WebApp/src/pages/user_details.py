from nicegui import ui
from src.services.data_webhook import game_plays, USERS
from src.models.user import User
from src.models.gameplay import GamePlay
from datetime import datetime
from typing import Tuple
import statistics
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# Table column definitions
TABLE_HEADERS = [
    {'name': 'index', 'label': '#', 'classes': 'flex-[0.05] min-w-[40px] flex-shrink-0'},
    {'name': 'timestamp', 'label': 'Timestamp', 'classes': 'flex-[0.12] min-w-[130px] flex-shrink-0'},
    {'name': 'level', 'label': 'Level', 'classes': 'flex-[0.06] min-w-[50px] flex-shrink-0'},
    {'name': 'response_times', 'label': 'Response Times', 'classes': 'flex-[0.50] min-w-[400px] flex-shrink-0'},
    {'name': 'warning_level', 'label': 'Status', 'classes': 'flex-[0.10] min-w-[100px] flex-shrink-0'},
]


def evaluate_game_score(level_reached: int, response_times: list[float]) -> float:
    """
    Evaluate a single gameplay session score (0-100).

    Scoring breakdown:
    - Level performance: 70% weight (level / 11 max)
    - Response time performance: 30% weight (faster = higher score)
    """
    valid_times = [t for t in response_times if t > 0]

    # Level component (70% weight) - max level is ~11
    MAX_LEVEL = 11
    level_score = min((level_reached / MAX_LEVEL) * 70, 70)

    # Response time component (30% weight)
    if valid_times:
        avg_response = statistics.mean(valid_times)
        if avg_response <= 0.3:
            response_score = 30
        elif avg_response >= 2.0:
            response_score = 0
        else:
            # Linear interpolation between 0.3s (30pts) and 2.0s (0pts)
            response_score = 30 * (1 - (avg_response - 0.3) / 1.7)
    else:
        response_score = 0

    return level_score + response_score


def calculate_warning_level(response_times: list[float], level_reached: int = 0) -> Tuple[str, str, str]:
    """Calculate warning level based on game score (combining level and response time)"""
    if not response_times:
        return "N/A", "text-gray-400 bg-gray-100", "No Time"

    try:
        valid_times = [t for t in response_times if t > 0]
        if not valid_times:
            return "N/A", "text-gray-400 bg-gray-100", "No Time"

        avg_time = statistics.mean(valid_times)
        avg_time_str = f"{avg_time:.3f}s"

        # Calculate score using both level and response time
        score = evaluate_game_score(level_reached, response_times)

        # Scoring thresholds:
        # - Good: score >= 55 (6+ levels with decent response time easily achieves this)
        # - Normal: score >= 35
        # - Bad: score < 35
        GOOD_THRESHOLD = 55
        NORMAL_THRESHOLD = 35

        if score >= GOOD_THRESHOLD:
            return "Good", "text-green-700 bg-green-100 font-semibold", avg_time_str
        elif score >= NORMAL_THRESHOLD:
            return "Normal", "text-yellow-700 bg-yellow-100 font-semibold", avg_time_str
        else:
            return "Bad", "text-red-700 bg-red-100 font-semibold", avg_time_str
    except Exception:
        return "Error", "text-red-500 bg-red-100", "Error"


def render_user_card(user: User):
    """Render user information card - compact version"""
    with ui.card().classes("p-3 items-center"):
        with ui.row().classes("w-full flex-nowrap items-center gap-3"):
            ui.image("/static/" + user.icon_file).classes("w-12 h-12").style(
                "border-radius: 50%;"
            )
            with ui.column().classes("gap-0"):
                ui.label(f"{user.name}").classes("text-lg font-bold")
                ui.label(f"ID: {user.id} | Device: {user.device_id}").classes("text-gray-400 text-xs")


def render_table_header():
    """Render table header row"""
    with ui.row().classes("w-full bg-gray-100 font-bold text-xs border-b border-gray-300 items-center flex-nowrap px-2"):
        for header in TABLE_HEADERS:
            with ui.element('div').classes(f"p-2 text-left {header['classes']} flex items-center justify-start h-full"):
                ui.label(header['label'])


def render_response_times_cell(response_times: list[float]):
    """Render response times as a mini sparkline chart"""
    if not response_times:
        ui.label("-").classes("text-gray-400")
        return

    valid_times = [t for t in response_times if t > 0]
    if not valid_times:
        ui.label("-").classes("text-gray-400")
        return

    # Create mini sparkline
    levels = list(range(1, len(valid_times) + 1))

    # Determine colors based on threshold
    colors = ['#22c55e' if t <= 0.5 else '#eab308' if t <= 1.5 else '#ef4444' for t in valid_times]

    fig = go.Figure()

    # Add line
    fig.add_trace(go.Scatter(
        x=levels,
        y=valid_times,
        mode='lines+markers',
        line=dict(color='#6366f1', width=1.5),
        marker=dict(size=3, color=colors),
        hovertemplate='L%{x}: %{y:.3f}s<extra></extra>'
    ))

    # Add threshold line
    fig.add_hline(y=0.5, line_dash="dot", line_color="rgba(34, 197, 94, 0.5)", line_width=1)

    fig.update_layout(
        height=40,
        width=320,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    with ui.row().classes("items-center gap-2"):
        ui.plotly(fig).classes("").style("width: 320px; height: 40px;")
        avg_time = statistics.mean(valid_times)
        ui.label(f"Avg: {avg_time:.2f}s").classes("text-xs text-gray-500")


def render_warning_level_cell(response_times: list[float], level_reached: int = 0):
    """Render warning level status badge"""
    status, status_class, avg_time_str = calculate_warning_level(response_times, level_reached)

    with ui.element('div').classes("flex items-center gap-2"):
        with ui.element('div').classes(f"text-sm py-1.5 px-3 rounded-full {status_class}").style("min-width: 80px; text-align: center;"):
            ui.label(status).classes("whitespace-nowrap")
        if avg_time_str != "No Time" and status != "Error":
            ui.label(f"({avg_time_str})").classes("text-xs text-gray-500 font-medium whitespace-nowrap")


def render_gameplay_row(index: int, play: GamePlay):
    """Render a single gameplay row"""
    row_classes = "w-full text-sm border-b border-gray-100 hover:bg-gray-50 py-[5px] transition-colors flex-nowrap px-2"

    with ui.row().classes(row_classes):
        for header in TABLE_HEADERS:
            field_name = header['name']
            with ui.element('div').classes(f"p-2 {header['classes']} flex flex-col items-start justify-start h-full"):

                if field_name == 'index':
                    ui.label(str(index)).classes("font-medium text-gray-800 whitespace-nowrap mt-[6px]")

                elif field_name == 'timestamp':
                    timestamp_str = play.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    ui.label(timestamp_str).classes("font-medium text-gray-800 whitespace-nowrap mt-[6px]")

                elif field_name == 'level':
                    ui.label(str(play.level_reached)).classes("font-medium text-gray-800 whitespace-nowrap mt-[6px]")

                elif field_name == 'response_times':
                    render_response_times_cell(play.response_times_seconds)

                elif field_name == 'warning_level':
                    render_warning_level_cell(play.response_times_seconds, play.level_reached)


def render_gameplay_table(plays: list[GamePlay]):
    """Render the gameplay data table"""
    with ui.column().classes("w-fit bg-white shadow-sm rounded-xl border border-gray-200 overflow-x-auto gap-0").style("max-width: calc(100% * 1.045)"):
        render_table_header()

        for index, play in enumerate(plays, 1):
            render_gameplay_row(index, play)


def calculate_delirium_risk_score(plays: list[GamePlay]) -> Tuple[float, str, str]:
    """
    Calculate delirium risk score based on multiple factors:
    - Response time trends (worsening = higher risk)
    - Performance variability
    - Recent vs historical comparison
    Returns: (score 0-100, risk level, description)
    """
    if len(plays) < 2:
        return 0, "Insufficient Data", "Need more sessions to assess risk"

    # Get average response times per session
    session_avgs = []
    for play in plays:
        valid_times = [t for t in play.response_times_seconds if t > 0]
        if valid_times:
            session_avgs.append(statistics.mean(valid_times))

    if len(session_avgs) < 2:
        return 0, "Insufficient Data", "Need more valid sessions"

    risk_score = 0

    # Factor 1: Recent performance trend (40% weight)
    recent = session_avgs[-3:] if len(session_avgs) >= 3 else session_avgs
    if len(recent) >= 2:
        trend = (recent[-1] - recent[0]) / len(recent)
        if trend > 0.5:  # Significant worsening
            risk_score += 40
        elif trend > 0.2:
            risk_score += 25
        elif trend > 0:
            risk_score += 10

    # Factor 2: Performance variability (30% weight)
    if len(session_avgs) >= 3:
        variability = statistics.stdev(session_avgs) / statistics.mean(session_avgs)
        if variability > 0.5:
            risk_score += 30
        elif variability > 0.3:
            risk_score += 20
        elif variability > 0.15:
            risk_score += 10

    # Factor 3: Absolute performance level (30% weight)
    latest_avg = session_avgs[-1]
    if latest_avg > 2.0:
        risk_score += 30
    elif latest_avg > 1.5:
        risk_score += 20
    elif latest_avg > 1.0:
        risk_score += 10

    # Determine risk level
    if risk_score >= 70:
        return risk_score, "High Risk", "Immediate attention recommended"
    elif risk_score >= 40:
        return risk_score, "Moderate Risk", "Monitor closely"
    elif risk_score >= 20:
        return risk_score, "Low Risk", "Continue regular monitoring"
    else:
        return risk_score, "Minimal Risk", "Performance is stable"


def calculate_performance_score(plays: list[GamePlay]) -> Tuple[float, str, str]:
    """
    Calculate overall performance score (0-100) with emphasis on levels reached.

    Scoring breakdown:
    - Level performance: 70% weight (best level / 11 max)
    - Response time performance: 30% weight (faster = higher score)

    Returns: (score, grade, description)
    """
    if not plays:
        return 0, "N/A", "No data available"

    all_times = []
    all_levels = []
    for play in plays:
        valid_times = [t for t in play.response_times_seconds if t > 0]
        all_times.extend(valid_times)
        all_levels.append(play.level_reached)

    if not all_levels:
        return 0, "N/A", "No valid gameplay data"

    # Level component (70% weight) - max level is ~11
    MAX_LEVEL = 11
    best_level = max(all_levels)
    avg_level = statistics.mean(all_levels)

    # Use weighted combination of best and average level
    level_metric = (best_level * 0.6 + avg_level * 0.4) / MAX_LEVEL
    level_score = min(level_metric * 70, 70)  # Cap at 70 points

    # Response time component (30% weight)
    # Scale: 0.3s or less = 30pts, 2.0s or more = 0pts
    if all_times:
        avg_response = statistics.mean(all_times)
        if avg_response <= 0.3:
            response_score = 30
        elif avg_response >= 2.0:
            response_score = 0
        else:
            # Linear interpolation between 0.3s (30pts) and 2.0s (0pts)
            response_score = 30 * (1 - (avg_response - 0.3) / 1.7)
    else:
        response_score = 0

    total_score = level_score + response_score

    # Determine grade
    if total_score >= 85:
        return total_score, "A+", "Excellent cognitive performance"
    elif total_score >= 75:
        return total_score, "A", "Very good performance"
    elif total_score >= 65:
        return total_score, "B+", "Good performance"
    elif total_score >= 55:
        return total_score, "B", "Above average performance"
    elif total_score >= 45:
        return total_score, "C+", "Average performance"
    elif total_score >= 35:
        return total_score, "C", "Below average performance"
    elif total_score >= 25:
        return total_score, "D", "Needs improvement"
    else:
        return total_score, "F", "Poor performance - monitor closely"


def render_performance_summary(plays: list[GamePlay]):
    """Render compact performance summary in a single card"""
    if not plays:
        return

    # Calculate metrics
    all_times = []
    all_levels = []
    for play in plays:
        valid_times = [t for t in play.response_times_seconds if t > 0]
        all_times.extend(valid_times)
        all_levels.append(play.level_reached)

    avg_response = statistics.mean(all_times) if all_times else 0
    best_level = max(all_levels) if all_levels else 0
    avg_level = statistics.mean(all_levels) if all_levels else 0
    total_sessions = len(plays)

    # Calculate performance score
    score, grade, score_desc = calculate_performance_score(plays)

    # Calculate consistency
    if len(all_levels) > 1:
        consistency = 100 - (statistics.stdev(all_levels) / statistics.mean(all_levels) * 100)
        consistency = max(0, min(100, consistency))
    else:
        consistency = 100

    # Determine colors
    perf_color = "text-green-600" if avg_response <= 0.5 else "text-yellow-600" if avg_response <= 1.5 else "text-red-600"
    cons_color = "text-green-600" if consistency >= 70 else "text-yellow-600" if consistency >= 50 else "text-red-600"

    # Determine score color
    if score >= 75:
        score_color = "text-green-600"
    elif score >= 55:
        score_color = "text-blue-600"
    elif score >= 35:
        score_color = "text-yellow-600"
    else:
        score_color = "text-red-600"

    with ui.card().classes("w-full p-3 mb-3"):
        ui.label("Performance Overview").classes("text-sm font-bold mb-2")
        with ui.row().classes("w-full justify-between"):
            with ui.column().classes("items-center flex-1"):
                with ui.row().classes("items-baseline gap-1"):
                    ui.label(f"{score:.0f}").classes(f"text-2xl font-bold {score_color}")
                    ui.label(f"({grade})").classes(f"text-sm font-semibold {score_color}")
                ui.label("Performance Score").classes("text-xs text-gray-500")
            with ui.column().classes("items-center flex-1"):
                ui.label(str(best_level)).classes("text-lg font-bold text-purple-600")
                ui.label(f"Best Level (Avg: {avg_level:.1f})").classes("text-xs text-gray-500")
            with ui.column().classes("items-center flex-1"):
                ui.label(f"{avg_response:.3f}s").classes(f"text-lg font-bold {perf_color}")
                ui.label("Avg Response").classes("text-xs text-gray-500")
            with ui.column().classes("items-center flex-1"):
                ui.label(str(total_sessions)).classes("text-lg font-bold text-blue-600")
                ui.label("Sessions").classes("text-xs text-gray-500")
            with ui.column().classes("items-center flex-1"):
                ui.label(f"{consistency:.0f}%").classes(f"text-lg font-bold {cons_color}")
                ui.label("Consistency").classes("text-xs text-gray-500")


def render_response_time_trend_chart(plays: list[GamePlay]):
    """Render response time trend line chart"""
    if len(plays) < 2:
        ui.label("Need at least 2 sessions for trend analysis").classes("text-gray-500 italic p-4")
        return

    session_data = []
    for i, play in enumerate(plays, 1):
        valid_times = [t for t in play.response_times_seconds if t > 0]
        if valid_times:
            session_data.append({
                'session': i,
                'avg_time': statistics.mean(valid_times),
                'min_time': min(valid_times),
                'max_time': max(valid_times),
                'date': play.timestamp.strftime("%m/%d %H:%M")
            })

    if len(session_data) < 2:
        return

    sessions = [d['session'] for d in session_data]
    avg_times = [d['avg_time'] for d in session_data]
    min_times = [d['min_time'] for d in session_data]
    max_times = [d['max_time'] for d in session_data]
    dates = [d['date'] for d in session_data]

    fig = go.Figure()

    # Add range area
    fig.add_trace(go.Scatter(
        x=sessions + sessions[::-1],
        y=max_times + min_times[::-1],
        fill='toself',
        fillcolor='rgba(99, 102, 241, 0.1)',
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo='skip',
        showlegend=False
    ))

    # Add average line
    fig.add_trace(go.Scatter(
        x=sessions,
        y=avg_times,
        mode='lines+markers',
        name='Avg Response Time',
        line=dict(color='#6366f1', width=3),
        marker=dict(size=8),
        text=dates,
        hovertemplate='Session %{x}<br>Avg: %{y:.3f}s<br>%{text}<extra></extra>'
    ))

    # Add threshold lines
    fig.add_hline(y=0.5, line_dash="dash", line_color="green",
                  annotation_text="Good (0.5s)", annotation_position="right")
    fig.add_hline(y=1.5, line_dash="dash", line_color="orange",
                  annotation_text="Warning (1.5s)", annotation_position="right")

    fig.update_layout(
        title="Response Time Trend",
        xaxis_title="Session",
        yaxis_title="Response Time (s)",
        height=300,
        margin=dict(l=40, r=40, t=40, b=40),
        showlegend=False
    )

    ui.plotly(fig).classes("w-full")


def render_level_progression_chart(plays: list[GamePlay]):
    """Render level progression bar chart"""
    if not plays:
        return

    sessions = list(range(1, len(plays) + 1))
    levels = [play.level_reached for play in plays]
    dates = [play.timestamp.strftime("%m/%d %H:%M") for play in plays]

    # Color based on performance
    colors = []
    for level in levels:
        if level >= 10:
            colors.append('#22c55e')  # green
        elif level >= 5:
            colors.append('#eab308')  # yellow
        else:
            colors.append('#ef4444')  # red

    fig = go.Figure(data=[
        go.Bar(
            x=sessions,
            y=levels,
            marker_color=colors,
            text=levels,
            textposition='auto',
            hovertemplate='Session %{x}<br>Level: %{y}<br>%{customdata}<extra></extra>',
            customdata=dates
        )
    ])

    fig.update_layout(
        title="Level Progression",
        xaxis_title="Session",
        yaxis_title="Level",
        height=200,
        margin=dict(l=30, r=10, t=30, b=30)
    )

    ui.plotly(fig).classes("w-full")


def render_delirium_risk_gauge(plays: list[GamePlay]):
    """Render delirium risk assessment gauge"""
    risk_score, risk_level, description = calculate_delirium_risk_score(plays)

    # Determine color
    if risk_score >= 70:
        color = "red"
        bar_color = "#ef4444"
    elif risk_score >= 40:
        color = "orange"
        bar_color = "#f97316"
    elif risk_score >= 20:
        color = "yellow"
        bar_color = "#eab308"
    else:
        color = "green"
        bar_color = "#22c55e"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Delirium Risk Score", 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': bar_color},
            'steps': [
                {'range': [0, 20], 'color': 'rgba(34, 197, 94, 0.3)'},
                {'range': [20, 40], 'color': 'rgba(234, 179, 8, 0.3)'},
                {'range': [40, 70], 'color': 'rgba(249, 115, 22, 0.3)'},
                {'range': [70, 100], 'color': 'rgba(239, 68, 68, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 2},
                'thickness': 0.75,
                'value': risk_score
            }
        }
    ))

    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=50, b=10)
    )

    with ui.card().classes("p-4 w-full"):
        with ui.row().classes("w-full items-center gap-6"):
            # Gauge on the left
            with ui.column().classes("flex-shrink-0"):
                ui.plotly(fig).classes("").style("width: 280px; height: 200px;")

            # Risk info on the right
            with ui.column().classes("flex-1 gap-2"):
                ui.label("Delirium Risk Assessment").classes("text-lg font-bold")
                risk_colors = {
                    "High Risk": "text-red-600 bg-red-100",
                    "Moderate Risk": "text-orange-600 bg-orange-100",
                    "Low Risk": "text-yellow-600 bg-yellow-100",
                    "Minimal Risk": "text-green-600 bg-green-100",
                    "Insufficient Data": "text-gray-600 bg-gray-100"
                }
                with ui.element('div').classes(f"px-4 py-2 rounded-lg {risk_colors.get(risk_level, '')} w-fit"):
                    ui.label(risk_level).classes("font-bold text-base")
                ui.label(description).classes("text-sm text-gray-600")


def render_response_time_distribution(plays: list[GamePlay]):
    """Render response time distribution histogram"""
    all_times = []
    for play in plays:
        all_times.extend([t for t in play.response_times_seconds if t > 0])

    if not all_times:
        return

    fig = go.Figure(data=[
        go.Histogram(
            x=all_times,
            nbinsx=20,
            marker_color='#6366f1',
            opacity=0.75
        )
    ])

    # Add threshold lines
    fig.add_vline(x=0.5, line_dash="dash", line_color="green",
                  annotation_text="Good", annotation_position="top")
    fig.add_vline(x=1.5, line_dash="dash", line_color="orange",
                  annotation_text="Warning", annotation_position="top")

    fig.update_layout(
        title="Response Time Distribution",
        xaxis_title="Response Time (s)",
        yaxis_title="Frequency",
        height=300,
        margin=dict(l=40, r=40, t=40, b=40)
    )

    ui.plotly(fig).classes("w-full")


def render_performance_heatmap(plays: list[GamePlay]):
    """Render performance heatmap showing response times per level across sessions"""
    if len(plays) < 2:
        return

    # Get max levels across all sessions
    max_level = max(play.level_reached for play in plays)
    max_level = min(max_level, 15)  # Cap at 15 for readability

    # Build heatmap data
    z_data = []
    session_labels = []

    for i, play in enumerate(plays[-10:], 1):  # Last 10 sessions
        row = []
        for level in range(max_level):
            if level < len(play.response_times_seconds):
                row.append(play.response_times_seconds[level])
            else:
                row.append(None)
        z_data.append(row)
        session_labels.append(f"S{i}")

    level_labels = [f"L{i+1}" for i in range(max_level)]

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=level_labels,
        y=session_labels,
        colorscale=[
            [0, '#22c55e'],      # green for fast
            [0.33, '#eab308'],   # yellow
            [0.66, '#f97316'],   # orange
            [1, '#ef4444']       # red for slow
        ],
        hoverongaps=False,
        hovertemplate='Session: %{y}<br>Level: %{x}<br>Time: %{z:.3f}s<extra></extra>'
    ))

    fig.update_layout(
        title="Response Time Heatmap",
        xaxis_title="Level",
        yaxis_title="Session",
        height=200,
        margin=dict(l=30, r=10, t=30, b=30)
    )

    ui.plotly(fig).classes("w-full")


def render_visualizations(plays: list[GamePlay]):
    """Render all data visualizations - compact layout"""
    if not plays:
        with ui.card().classes("w-full p-4 text-center"):
            ui.label("No gameplay data available").classes("text-gray-500")
        return

    # Compact Performance Summary
    render_performance_summary(plays)

    # Charts row: Level Trend and Heatmap
    with ui.row().classes("w-full gap-3 mb-3"):
        with ui.card().classes("flex-1 p-2"):
            render_level_progression_chart(plays)
        with ui.card().classes("flex-1 p-2"):
            if len(plays) >= 2:
                render_performance_heatmap(plays)
            else:
                ui.label("Need 2+ sessions for heatmap").classes("text-gray-400 text-xs p-4")

    # Delirium Risk Panel - full width for better layout
    with ui.row().classes("w-full gap-3 mb-3"):
        with ui.column().classes("flex-1"):
            render_delirium_risk_gauge(plays)


def user_details(userid: int):
    """Display user details page with gameplay history"""
    # Find user by id
    user = next((u for u in USERS if u.id == userid), None)

    if not user:
        ui.label(f"User '{userid}' not found").classes("text-red-500 text-xl")
        return

    # Get user's gameplays
    plays = game_plays.get(user, [])

    # User card
    render_user_card(user)

    ui.separator()

    # Data Visualizations section
    render_visualizations(plays)

    ui.separator()

    # Gameplay history section
    ui.label("Gameplay History").classes("text-xl font-bold mt-4 mb-2")

    if plays:
        render_gameplay_table(plays)
    else:
        ui.label("No gameplay records yet").classes("text-gray-500 italic")

    # Refresh button
    ui.button("Refresh", on_click=lambda: ui.navigate.reload()).classes(
        "mt-4 text-white font-semibold py-2 px-5 rounded-lg "
        "!bg-[hsl(240_5.9%_10%)] !hover:bg-[hsl(240_5.9%_5%)] "
        "shadow-md transition-colors duration-200"
    )
