from __future__ import annotations

from html import escape

import streamlit as st

from .models import Match, MatchStatus, Player
from .tournament import name_for, round_label


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --chalk: #fffaf0;
            --ink: #0f1419;
            --muted: #5f6770;
            --blue: #385da8;
            --blue-soft: #d7defd;
            --tab: #f3f0ee;
            --card: #f2f2f2;
            --line: rgba(15, 20, 25, 0.13);
        }

        .stApp {
            background: #ffffff;
            color: var(--ink);
        }

        header[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"] {
            display: none;
        }

        .print-button {
            display: none !important;
        }

        .block-container {
            max-width: none;
            margin: 0;
            padding: 0 0 3rem;
            background: #ffffff;
            border: 0;
            border-radius: 0;
            box-shadow: none;
        }

        section.main > div {
            color: var(--ink);
        }

        h1, h2, h3 {
            color: var(--ink);
            letter-spacing: 0;
        }

        h3 {
            margin-top: 0.4rem;
        }

        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stMarkdownContainer"] li,
        label,
        .stRadio,
        .stCheckbox {
            color: var(--ink);
        }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"],
        [data-testid="stSidebar"] *,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {
            color: var(--ink) !important;
        }

        [data-testid="stSidebar"] code {
            background: #10151d !important;
            color: #79ff9f !important;
            border-radius: 6px;
            padding: 3px 7px;
        }

        .stTabs [data-baseweb="tab-list"] {
            justify-content: center;
            gap: 12px;
            background: #ffffff;
            border-bottom: 1px solid #e1e1e1;
            border-radius: 0;
            padding: 24px 16px;
        }

        .stTabs [data-baseweb="tab"] {
            background: var(--tab);
            border-radius: 11px;
            color: var(--ink);
            font-weight: 800;
            min-width: 124px;
            padding: 14px 20px;
        }

        .stTabs [aria-selected="true"] {
            background: var(--blue-soft);
            color: #2447a8;
            box-shadow: inset 0 -4px 0 #3953c6;
        }

        .event-header {
            height: 102px;
            background:
                linear-gradient(126deg, rgba(255,255,255,0.26) 72%, rgba(255,255,255,0.0) 72%),
                linear-gradient(115deg, #315f95 0%, #3a6da2 50%, #9db6ce 100%);
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            padding: 0 42px;
        }

        .event-left {
            display: flex;
            align-items: center;
            gap: 16px;
            min-width: 0;
        }

        .event-back {
            font-size: 2.4rem;
            line-height: 1;
            font-weight: 300;
            opacity: 0.95;
        }

        .event-logo {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background:
                radial-gradient(circle at 64% 35%, #ffffff 0 16%, transparent 17%),
                conic-gradient(from 30deg, #f05a28, #ffffff, #2786c7, #39a64a, #f6c641, #ffffff, #f05a28);
            box-shadow: inset 0 0 0 5px rgba(255,255,255,.88), 0 5px 16px rgba(0,0,0,.18);
            flex: 0 0 auto;
        }

        .event-copy {
            min-width: 0;
        }

        .event-title {
            margin: 0;
            color: #ffffff;
            font-size: 1.55rem;
            line-height: 1.05;
            font-weight: 900;
            white-space: nowrap;
        }

        .event-date {
            margin: 10px 0 0;
            color: #ffffff;
            font-size: 1.05rem;
            font-weight: 700;
        }

        div[data-testid="stVerticalBlock"] > div:has(.fixture-strip),
        div[data-testid="stVerticalBlock"] > div:has(.metric-tile),
        div[data-testid="stVerticalBlock"] > div:has(.match-card),
        div[data-testid="stVerticalBlock"] > div:has(.team-list),
        div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stForm"]),
        div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stAlert"]) {
            max-width: 1180px;
            margin-left: auto;
            margin-right: auto;
            padding-left: 24px;
            padding-right: 24px;
        }

        div[data-testid="stForm"],
        div[data-testid="stExpander"] {
            background: rgba(255, 253, 247, 0.98);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 12px;
        }

        .match-card, .panel, .metric-tile {
            background: rgba(255, 253, 247, 0.98);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 14px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.10);
        }

        .fixture-strip {
            background: #ffffff;
            border: 1px solid rgba(20, 35, 31, 0.10);
            border-left: 8px solid #4057c8;
            border-radius: 8px;
            padding: 16px 20px 18px;
            margin-bottom: 20px;
            box-shadow: none;
            overflow: visible;
        }

        .fixture-eyebrow {
            color: var(--blue);
            font-size: 0.76rem;
            font-weight: 900;
            margin: 0 0 6px 0;
            text-transform: uppercase;
        }

        .fixture-title {
            font-size: clamp(1.55rem, 4.4vw, 3.5rem);
            font-weight: 900;
            line-height: 1.08;
            margin: 0;
            color: #10201c;
            text-transform: uppercase;
        }

        .fixture-subtitle {
            color: #3e544d;
            font-size: 1rem;
            line-height: 1.45;
            margin: 6px 0 0 0;
            max-width: 760px;
        }

        .badge {
            display: inline-block;
            border-radius: 999px;
            padding: 3px 9px;
            font-size: 0.78rem;
            font-weight: 700;
            background: #e2f5ec;
            color: #0c5545;
            border: 1px solid rgba(15, 107, 85, 0.22);
        }

        .badge-wait {
            background: #fff0c9;
            color: #6f4d00;
            border-color: rgba(111, 77, 0, 0.25);
        }

        .player-line {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            padding: 9px 10px;
            margin: 6px 0;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.66);
            border: 1px solid rgba(24, 33, 31, 0.08);
            min-height: 42px;
            font-weight: 750;
        }

        .winner {
            outline: 2px solid rgba(246, 216, 79, 0.95);
            background: #fff7be;
            font-weight: 800;
        }

        .loser {
            opacity: 0.7;
        }

        .round-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 12px;
        }

        .bracket-scroll {
            overflow-x: auto;
            padding: 4px 0 14px;
            margin-bottom: 18px;
        }

        .bracket-board {
            display: flex;
            gap: 16px;
            align-items: flex-start;
            min-width: max-content;
        }

        .bracket-column {
            width: 260px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .bracket-column h4 {
            position: sticky;
            top: 0;
            z-index: 1;
            margin: 0;
            padding: 10px 12px;
            background: var(--ink);
            color: var(--chalk);
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 900;
            text-transform: uppercase;
        }

        .bracket-match {
            position: relative;
            background: rgba(255, 253, 247, 0.98);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 12px;
            box-shadow: 0 8px 22px rgba(0, 0, 0, 0.10);
        }

        .bracket-match::after {
            content: "";
            position: absolute;
            right: -16px;
            top: 50%;
            width: 16px;
            height: 1px;
            background: rgba(255, 250, 240, 0.72);
        }

        .bracket-column:last-child .bracket-match::after {
            display: none;
        }

        .bracket-match-label {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 900;
            margin-bottom: 8px;
        }

        .bracket-player {
            min-height: 36px;
            padding: 8px 10px;
            margin-top: 6px;
            background: #f8faf6;
            border: 1px solid rgba(20, 35, 31, 0.10);
            border-radius: 7px;
            font-weight: 800;
            color: var(--ink);
        }

        .winner-slot {
            background: #fff7be;
            border-color: rgba(246, 216, 79, 0.9);
            box-shadow: inset 0 0 0 1px rgba(246, 216, 79, 0.75);
        }

        .bracket-status {
            display: inline-block;
            margin-top: 10px;
            border-radius: 999px;
            padding: 3px 9px;
            font-size: 0.75rem;
            font-weight: 900;
        }

        .bracket-status.is-complete {
            background: #e2f5ec;
            color: #0c5545;
        }

        .bracket-status.is-pending {
            background: #fff0c9;
            color: #6f4d00;
        }

        .march-shell {
            overflow-x: auto;
            overflow-y: hidden;
            background: #ffffff;
            border: 0;
            border-radius: 0;
            padding: 0 0 34px;
            margin: 0 0 18px;
            box-shadow: none;
        }

        .march-board {
            display: flex;
            align-items: stretch;
            gap: 30px;
            min-width: max-content;
            padding: 0 0 12px;
        }

        .march-column {
            width: 254px;
            display: flex;
            flex-direction: column;
        }

        .march-column h4 {
            position: sticky;
            top: 0;
            z-index: 2;
            margin: 0 0 44px;
            padding: 10px 0 20px;
            background: #ffffff;
            border-bottom: 0;
            color: #050505;
            font-size: 1.08rem;
            font-weight: 700;
            text-align: center;
        }

        .march-stack {
            display: flex;
            flex-direction: column;
            justify-content: space-around;
            gap: 30px;
            height: 100%;
            min-height: 760px;
        }

        .march-match {
            position: relative;
            background: var(--card);
            border-radius: 24px;
            padding: 14px 18px 12px;
            min-height: 150px;
            box-shadow: none;
        }

        .march-match::after {
            content: "";
            position: absolute;
            right: -31px;
            top: 50%;
            width: 31px;
            height: 1px;
            background: #bfc4c9;
        }

        .right-side .march-match::after {
            right: auto;
            left: -29px;
        }

        .final-side .march-match::after,
        .march-column:last-child .march-match::after {
            display: none;
        }

        .march-meta {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            color: #4f5961;
            font-size: 0.9rem;
            margin-bottom: 12px;
        }

        .march-player {
            display: flex;
            align-items: center;
            min-height: 38px;
            padding: 6px 0;
            color: #050505;
            font-size: 1.1rem;
            font-weight: 650;
        }

        .march-player::before {
            content: "";
            width: 22px;
            height: 16px;
            margin-right: 12px;
            border-radius: 2px;
            background:
                linear-gradient(90deg, #dde1e5 0 32%, transparent 32%),
                linear-gradient(#f8f8f8 0 33%, #315f95 33% 66%, #f8f8f8 66%);
            box-shadow: 0 0 0 1px rgba(0,0,0,.08);
            flex: 0 0 auto;
        }

        .march-player span {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .march-player.winner-slot {
            font-weight: 900;
        }

        .march-player.winner-slot::before {
            width: 22px;
            height: 16px;
            margin-right: 12px;
            border-radius: 2px;
            background:
                linear-gradient(90deg, #dde1e5 0 32%, transparent 32%),
                linear-gradient(#ffffff 0 33%, #4057c8 33% 66%, #ffffff 66%);
        }

        .march-line {
            height: 1px;
            margin-top: 8px;
            background: #d7d7d7;
        }

        .march-footer {
            color: #59616a;
            font-size: 0.9rem;
            margin-top: 10px;
        }

        .march-line.is-complete {
            background: #4057c8;
        }

        .team-list {
            columns: 2 180px;
            margin-top: 8px;
            background: rgba(255,253,247,0.94);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 12px 14px;
        }

        .small-muted {
            color: var(--muted);
            font-size: 0.86rem;
        }

        div.stButton > button,
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 8px;
            font-weight: 850;
            min-height: 42px;
        }

        input, textarea {
            border-radius: 8px !important;
        }

        div[data-testid="stAlert"] {
            background: #e9f3ff;
            border: 1px solid rgba(36, 87, 197, 0.20);
            border-radius: 8px;
            color: var(--ink);
        }

        div[data-testid="stAlert"] * {
            color: var(--ink) !important;
        }

        @media (max-width: 720px) {
            .block-container {
                padding: 0 0 2rem;
            }
            .event-header {
                height: 94px;
                padding: 0 16px;
            }
            .event-back {
                display: none;
            }
            .event-logo {
                width: 52px;
                height: 52px;
            }
            .event-title {
                font-size: 1.12rem;
                white-space: normal;
            }
            .event-date {
                font-size: 0.92rem;
                margin-top: 6px;
            }
            .stTabs [data-baseweb="tab-list"] {
                justify-content: flex-start;
                overflow-x: auto;
                padding: 18px 12px;
            }
            .stTabs [data-baseweb="tab"] {
                min-width: 104px;
                padding: 12px 14px;
            }
            .fixture-strip {
                padding: 16px 14px 18px;
                margin-top: 0.5rem;
                margin-bottom: 16px;
                border-left-width: 10px;
            }
            .fixture-eyebrow {
                display: none;
            }
            .fixture-title {
                font-size: 1.65rem;
                line-height: 1.12;
            }
            .fixture-subtitle {
                font-size: 1rem;
                line-height: 1.55;
            }
            .bracket-column {
                width: 230px;
            }
            .march-shell {
                border-radius: 0;
                margin-left: 0;
                margin-right: 0;
            }
            .march-board {
                gap: 24px;
            }
            .march-column {
                width: 230px;
            }
            .march-stack {
                min-height: 650px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def event_header() -> None:
    st.markdown(
        """
        <div class="event-header">
            <div class="event-left">
                <div class="event-back">&#8249;</div>
                <div class="event-logo" aria-hidden="true"></div>
                <div class="event-copy">
                    <p class="event-title">Cumple Mundial FC</p>
                    <p class="event-date">Torneo de cumpleanos</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, eyebrow: str = "Torneo") -> None:
    safe_title = escape(title)
    safe_subtitle = escape(subtitle)
    safe_eyebrow = escape(eyebrow)
    st.markdown(
        f"""
        <div class="fixture-strip">
            <p class="fixture-eyebrow">{safe_eyebrow}</p>
            <p class="fixture-title">{safe_title}</p>
            <p class="fixture-subtitle">{safe_subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_tile(label: str, value: str | int) -> None:
    safe_label = escape(str(label))
    safe_value = escape(str(value))
    st.markdown(
        f"""
        <div class="metric-tile">
            <div class="small-muted">{safe_label}</div>
            <div style="font-size: 1.8rem; font-weight: 900;">{safe_value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_match_card(match: Match, names: dict[int, str], bracket_size: int) -> None:
    label = escape(round_label(match.round_number, bracket_size))
    status = "Cerrado" if match.status == MatchStatus.COMPLETE else "Pendiente"
    status_class = "badge" if match.status == MatchStatus.COMPLETE else "badge badge-wait"
    a_class = "player-line"
    b_class = "player-line"
    if match.winner_id == match.player_a_id:
        a_class += " winner"
        b_class += " loser"
    elif match.winner_id == match.player_b_id:
        b_class += " winner"
        a_class += " loser"
    player_a = escape(name_for(names, match.player_a_id))
    player_b = escape(name_for(names, match.player_b_id))
    note = escape(match.note or "Sin juego anotado")

    st.markdown(
        f"""
        <div class="match-card">
            <div style="display:flex; justify-content:space-between; gap:8px; align-items:center;">
                <strong>{label} #{match.position}</strong>
                <span class="{status_class}">{status}</span>
            </div>
            <div class="{a_class}"><span>{player_a}</span></div>
            <div class="{b_class}"><span>{player_b}</span></div>
            <div class="small-muted">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def player_options(players: list[Player]) -> dict[str, int]:
    return {player.name: player.id for player in players}
