from __future__ import annotations

import sqlite3
from collections import defaultdict
from html import escape
from pathlib import Path

import streamlit as st

try:
    from streamlit_sortables import sort_items
except ImportError:  # pragma: no cover - optional UI dependency
    sort_items = None

from src import db
from src.models import Match, MatchStatus, TournamentStatus
from src.tournament import (
    advance_round,
    assign_representative,
    current_losers_without_rep,
    name_for,
    player_name_map,
    representative_lookup,
    resolve_representative,
    round_can_advance,
    round_label,
    start_tournament,
    teams_by_alive_player,
)
from src.ui import apply_theme, event_header, hero, metric_tile, render_match_card


st.set_page_config(page_title="Cumple Mundial", layout="wide", initial_sidebar_state="collapsed")


def get_connection() -> sqlite3.Connection:
    conn = db.connect()
    db.init_db(conn)
    return conn


def rerun() -> None:
    st.rerun()


def reset_panel(conn: sqlite3.Connection, location: str = "main") -> None:
    with st.expander("Administracion"):
        st.caption("Reinicio total del torneo.")
        confirm = st.text_input("Escribi REINICIAR para borrar todo", key=f"{location}-reset-confirm")
        if st.button("Reiniciar torneo", disabled=confirm != "REINICIAR", use_container_width=True, key=f"{location}-reset-button"):
            db.reset_db(conn)
            st.success("Torneo reiniciado")
            rerun()


def registration_view(conn: sqlite3.Connection) -> None:
    players = db.list_players(conn)
    hero(
        "Cumple Mundial",
        "Inscripcion abierta. Carga nombres desde el celu; cuando esten todos, sorteas el cuadro.",
    )

    metric_tile("Jugadores anotados", len(players))

    left, right = st.columns([0.95, 1.35], gap="large")
    with left:
        st.markdown("### Entrada")
        with st.form("add-player", clear_on_submit=True):
            name = st.text_input("Nombre", placeholder="Ej: Roman", label_visibility="collapsed")
            submitted = st.form_submit_button("Agregar participante", type="primary", use_container_width=True)
        if submitted:
            try:
                db.add_player(conn, name)
                st.toast("Participante agregado")
                rerun()
            except sqlite3.IntegrityError:
                st.error("Ese nombre ya esta cargado.")
            except ValueError as exc:
                st.error(str(exc))

        st.markdown("### Sorteo")
        st.caption("Cierra la inscripcion y arma el cuadro con byes automaticos si hacen falta.")
        if len(players) < 2:
            st.button("Sortear cuadro", disabled=True, use_container_width=True)
            st.info("Necesitas al menos 2 participantes.")
        else:
            if st.button("Sortear cuadro", type="primary", use_container_width=True):
                try:
                    start_tournament(conn)
                    st.toast("Cuadro sorteado")
                    rerun()
                except ValueError as exc:
                    st.error(str(exc))

    with right:
        st.markdown("### Lista de llegada")
        search = st.text_input(
            "Buscar anotado",
            placeholder="Escribi un nombre para revisar",
            key="player-search",
        )
        clean_search = search.strip().lower()
        visible_players = [
            player
            for player in players
            if not clean_search or clean_search in player.name.lower()
        ]
        if not players:
            st.info("Todavia no hay participantes. El primer nombre abre la mesa.")
        elif clean_search and not visible_players:
            st.info("No hay ningun anotado con ese nombre.")
        else:
            st.caption(f"Mostrando {len(visible_players)} de {len(players)} anotados.")
        for player in visible_players:
            row = st.columns([0.76, 0.24], vertical_alignment="center")
            row[0].markdown(f"**{player.name}**")
            if row[1].button("Borrar", key=f"delete-{player.id}", use_container_width=True):
                db.delete_player(conn, player.id)
                rerun()


def result_form(conn: sqlite3.Connection, match_id: int, names: dict[int, str], key_prefix: str = "result") -> None:
    matches = {match.id: match for match in db.list_matches(conn)}
    match = matches[match_id]
    candidates = [pid for pid in (match.player_a_id, match.player_b_id) if pid is not None]
    if match.status == MatchStatus.COMPLETE or len(candidates) < 2:
        return

    labels = {name_for(names, pid): pid for pid in candidates}
    with st.form(f"{key_prefix}-result-{match.id}"):
        winner_label = st.radio("Quien gano?", list(labels.keys()), horizontal=True)
        note = st.text_input("Juego o nota", placeholder="Ej: penales, truco, ping pong")
        pledge_done = st.checkbox("Hizo medio fondo blanco", value=False)
        submitted = st.form_submit_button("Guardar resultado", type="primary", use_container_width=True)
    if submitted:
        winner_id = labels[winner_label]
        loser_id = next(pid for pid in candidates if pid != winner_id)
        db.update_match_result(conn, match.id, winner_id, loser_id, note, pledge_done)
        st.toast("Partido cerrado")
        rerun()


def representatives_panel(conn: sqlite3.Connection, names: dict[int, str], key_prefix: str = "representatives") -> None:
    state = db.get_state(conn)
    matches = db.list_matches(conn, state.current_round)
    if len(matches) == 1 and matches[0].status == MatchStatus.COMPLETE:
        st.success("Final cerrada. No hace falta asignar representante: el campeon conserva su bando.")
        return

    pending = current_losers_without_rep(conn)
    if not pending:
        st.success("Todos los eliminados de esta ronda ya tienen representante.")
        return

    alive_ids = sorted({match.winner_id for match in db.list_matches(conn, state.current_round) if match.winner_id})
    alive_labels = {name_for(names, pid): pid for pid in alive_ids}
    st.warning(f"Faltan {len(pending)} representante(s).")
    for match in pending:
        loser_name = name_for(names, match.loser_id)
        with st.form(f"{key_prefix}-rep-{match.id}"):
            selected = st.selectbox(f"Representante de {loser_name}", list(alive_labels.keys()))
            submitted = st.form_submit_button("Guardar representante", use_container_width=True)
        if submitted:
            try:
                assign_representative(conn, match.loser_id, alive_labels[selected], match.id)
                st.toast("Representante guardado")
                rerun()
            except ValueError as exc:
                st.error(str(exc))


def drag_style() -> str:
    return """
    .sortable-component { gap: 14px; align-items: flex-start; overflow-x: auto; padding: 4px 0 14px; }
    .sortable-container { min-width: 220px; background: #f1f1f1; border: 0; border-radius: 18px; padding: 12px; }
    .sortable-container-header { font-weight: 900; color: #050505; margin-bottom: 10px; font-size: 14px; }
    .sortable-container-body, .sortable-container-boy { min-height: 68px; display: flex; flex-direction: column; gap: 8px; }
    .sortable-item { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 10px 12px; font-weight: 850; color: #050505; box-shadow: 0 1px 0 rgba(0,0,0,.04); cursor: grab; }
    """


def current_round_view(conn: sqlite3.Connection) -> None:
    state = db.get_state(conn)
    names = player_name_map(conn)
    matches = db.list_matches(conn, state.current_round)
    can_advance, reason = round_can_advance(conn)

    tab_board, tab_control, tab_teams = st.tabs(["Cuadro", "Partidos", "Bandos"])

    with tab_board:
        render_bracket(conn, names)
        render_final_winner_team_preview(conn, names, matches)
        render_board_actions(conn, names, matches, can_advance, reason)

    with tab_control:
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            metric_tile("Ronda actual", state.current_round)
        with k2:
            metric_tile("Partidos", len(matches))
        with k3:
            metric_tile("Abiertos", sum(1 for match in matches if match.status == MatchStatus.PENDING))
        with k4:
            metric_tile("Representantes pendientes", len(current_losers_without_rep(conn)))

        st.markdown("### Partidos")
        for match in matches:
            with st.expander(f"Partido {match.position}: {name_for(names, match.player_a_id)} vs {name_for(names, match.player_b_id)}", expanded=match.status == MatchStatus.PENDING):
                render_match_card(match, names, state.bracket_size)
                result_form(conn, match.id, names, "control")

        st.markdown("### Representantes")
        representatives_panel(conn, names, "control")

        st.markdown("### Avance")
        if can_advance:
            st.success(reason)
            if st.button("Avanzar ronda", type="primary", use_container_width=True):
                try:
                    advance_round(conn)
                    st.toast("Ronda avanzada")
                    rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.info(reason)
            st.button("Avanzar ronda", disabled=True, use_container_width=True)

    with tab_teams:
        render_teams(conn, names)


def render_board_actions(
    conn: sqlite3.Connection,
    names: dict[int, str],
    matches: list[Match],
    can_advance: bool,
    reason: str,
) -> None:
    state = db.get_state(conn)
    st.markdown("### Acciones del cuadro")
    action_tabs = st.tabs(["Ganadores", "Bandos", "Avance"])

    with action_tabs[0]:
        pending_matches = [
            match
            for match in matches
            if match.status == MatchStatus.PENDING and len(match_players(match)) == 2
        ]
        if not pending_matches:
            st.success("No quedan partidos abiertos para cargar en esta ronda.")
        else:
            cols = st.columns(2)
            for index, match in enumerate(pending_matches):
                with cols[index % 2]:
                    result_form(conn, match.id, names, "board")

    with action_tabs[1]:
        representatives_panel(conn, names, "board")

    with action_tabs[2]:
        if can_advance:
            st.success(reason)
            if st.button("Avanzar ronda", type="primary", use_container_width=True, key="board-advance-round"):
                try:
                    advance_round(conn)
                    st.toast("Ronda avanzada")
                    rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.info(reason)
            st.button("Avanzar ronda", disabled=True, use_container_width=True, key="board-advance-round-disabled")

        if state.current_round < max(1, state.bracket_size.bit_length() - 1):
            render_drag_advancement(conn, names)


def render_final_winner_team_preview(conn: sqlite3.Connection, names: dict[int, str], matches: list[Match]) -> None:
    if len(matches) != 1:
        return
    final_match = matches[0]
    if final_match.status != MatchStatus.COMPLETE or final_match.winner_id is None:
        return
    render_team_for_leader(conn, names, final_match.winner_id, "Bando ganador")


def match_players(match: Match) -> list[int]:
    return [pid for pid in (match.player_a_id, match.player_b_id) if pid is not None]


def rounds_for_bracket(bracket_size: int) -> list[int]:
    round_count = max(1, bracket_size.bit_length() - 1)
    return list(range(1, round_count + 1))


def matches_grouped_by_round(conn: sqlite3.Connection) -> dict[int, list[Match]]:
    grouped: dict[int, list[Match]] = defaultdict(list)
    for match in db.list_matches(conn):
        grouped[match.round_number].append(match)
    return grouped


def placeholder_for_slot(round_number: int, position: int, slot: str, bracket_size: int) -> str:
    if round_number <= 1:
        return "Bye"
    previous_position = (position * 2) - (1 if slot == "a" else 0)
    return f"W {round_label(round_number - 1, bracket_size)} #{previous_position}"


def bracket_player_text(match: Match, names: dict[int, str], slot: str, bracket_size: int) -> str:
    player_id = match.player_a_id if slot == "a" else match.player_b_id
    if player_id is not None:
        return name_for(names, player_id)
    return placeholder_for_slot(match.round_number, match.position, slot, bracket_size)


def match_for_position(grouped: dict[int, list[Match]], round_number: int, position: int) -> Match:
    for match in grouped.get(round_number, []):
        if match.position == position:
            return match
    return Match(
        id=0,
        round_number=round_number,
        position=position,
        player_a_id=None,
        player_b_id=None,
        winner_id=None,
        loser_id=None,
        status=MatchStatus.PENDING,
        note="",
        pledge_done=False,
    )


def render_bracket_match(match: Match, names: dict[int, str], bracket_size: int) -> str:
    status_class = "is-complete" if match.status == MatchStatus.COMPLETE else "is-pending"
    a_class = "winner-slot" if match.winner_id and match.winner_id == match.player_a_id else ""
    b_class = "winner-slot" if match.winner_id and match.winner_id == match.player_b_id else ""
    match_status = "Cerrado" if match.status == MatchStatus.COMPLETE else "Proximamente"
    match_time = "FT" if match.status == MatchStatus.COMPLETE else "--:--"
    return (
        "<article class='march-match'>"
        "<div class='march-meta'>"
        f"<span>{escape(round_label(match.round_number, bracket_size))} #{match.position}</span>"
        f"<span>{match_time}</span>"
        "</div>"
        f"<div class='march-player {a_class}'><span>{escape(bracket_player_text(match, names, 'a', bracket_size))}</span></div>"
        f"<div class='march-player {b_class}'><span>{escape(bracket_player_text(match, names, 'b', bracket_size))}</span></div>"
        f"<div class='march-line {status_class}'></div>"
        f"<div class='march-footer'>{match_status}</div>"
        "</article>"
    )


def render_bracket_column(
    grouped: dict[int, list[Match]],
    names: dict[int, str],
    bracket_size: int,
    round_number: int,
    positions: list[int],
    side: str,
) -> str:
    label = round_label(round_number, bracket_size)
    html = [f"<section class='march-column {side}'><h4>{escape(label)}</h4><div class='march-stack'>"]
    for position in positions:
        html.append(render_bracket_match(match_for_position(grouped, round_number, position), names, bracket_size))
    html.append("</div></section>")
    return "".join(html)


def render_bracket(conn: sqlite3.Connection, names: dict[int, str]) -> None:
    state = db.get_state(conn)
    grouped = matches_grouped_by_round(conn)
    total_rounds = max(1, state.bracket_size.bit_length() - 1)
    html = ["<div class='march-shell'><div class='march-board'>"]
    for round_number in range(1, total_rounds):
        match_count = max(1, state.bracket_size // (2**round_number))
        left_positions = list(range(1, (match_count // 2) + 1))
        html.append(render_bracket_column(grouped, names, state.bracket_size, round_number, left_positions, "left-side"))

    html.append(
        render_bracket_column(
            grouped,
            names,
            state.bracket_size,
            total_rounds,
            [1],
            "final-side",
        )
    )

    for round_number in range(total_rounds - 1, 0, -1):
        match_count = max(1, state.bracket_size // (2**round_number))
        right_positions = list(range((match_count // 2) + 1, match_count + 1))
        html.append(render_bracket_column(grouped, names, state.bracket_size, round_number, right_positions, "right-side"))

    html.append("</div></div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_drag_advancement(conn: sqlite3.Connection, names: dict[int, str]) -> None:
    if sort_items is None:
        st.info("Para arrastrar nombres instala dependencias con: pip install -r requirements.txt")
        return

    state = db.get_state(conn)
    if state.status != TournamentStatus.IN_PROGRESS:
        return

    current_matches = db.list_matches(conn, state.current_round)
    if len(current_matches) <= 1:
        return

    next_round = state.current_round + 1
    next_matches = db.list_matches(conn, next_round)
    next_match_count = max(1, len(current_matches) // 2)
    assigned_next_ids = {
        player_id
        for match in next_matches
        for player_id in match_players(match)
    }

    player_by_name = {name: pid for pid, name in names.items()}
    containers = []

    for match in current_matches:
        header = f"{round_label(match.round_number, state.bracket_size)} #{match.position}"
        draggable_players = [match.winner_id] if match.status == MatchStatus.COMPLETE and match.winner_id else match_players(match)
        items = [name_for(names, pid) for pid in draggable_players if pid not in assigned_next_ids]
        containers.append({"header": header, "items": items})

    for position in range(1, next_match_count + 1):
        existing = next_matches[position - 1] if position <= len(next_matches) else None
        header = f"{round_label(next_round, state.bracket_size)} #{position}"
        items = [name_for(names, pid) for pid in match_players(existing)] if existing else []
        containers.append({"header": header, "items": items})

    st.markdown("### Mover ganadores")
    st.caption("Arrastra cada ganador a su partido de la siguiente ronda y despues guarda.")
    sorted_containers = sort_items(
        containers,
        multi_containers=True,
        direction="horizontal",
        key=f"drag-round-{state.current_round}",
        custom_style=drag_style(),
    )

    if st.button("Guardar movimientos del bracket", type="primary", use_container_width=True):
        try:
            save_drag_advancement(conn, current_matches, sorted_containers, names, player_by_name, state.bracket_size)
            st.toast("Bracket actualizado")
            rerun()
        except ValueError as exc:
            st.error(str(exc))


def save_drag_advancement(
    conn: sqlite3.Connection,
    current_matches: list[Match],
    sorted_containers: list[dict[str, list[str]]],
    names: dict[int, str],
    player_by_name: dict[str, int],
    bracket_size: int,
) -> None:
    state = db.get_state(conn)
    next_round = state.current_round + 1
    next_headers = {
        f"{round_label(next_round, bracket_size)} #{position}": position
        for position in range(1, max(1, len(current_matches) // 2) + 1)
    }

    next_slots: dict[int, list[int]] = {}
    seen_next_players: set[int] = set()

    for container in sorted_containers:
        header = container["header"]
        items = container["items"]
        if header in next_headers:
            player_ids = [player_by_name[item] for item in items]
            if len(player_ids) > 2:
                raise ValueError("Cada partido de la siguiente ronda puede tener como maximo 2 jugadores.")
            for player_id in player_ids:
                if player_id in seen_next_players:
                    raise ValueError("Un jugador no puede estar en dos slots de la siguiente ronda.")
                seen_next_players.add(player_id)
            next_slots[next_headers[header]] = player_ids

    moved_winners: dict[int, int] = {}
    for match in current_matches:
        winners_in_next = set(match_players(match)) & seen_next_players
        if not winners_in_next:
            continue
        if len(winners_in_next) > 1:
            raise ValueError("Move un solo ganador por partido hacia la siguiente ronda.")
        moved_winners[match.id] = next(iter(winners_in_next))

    for match in current_matches:
        if match.id not in moved_winners:
            continue
        players = match_players(match)
        winner_id = moved_winners[match.id]
        if winner_id not in players:
            raise ValueError("Movimiento invalido: el ganador no pertenece a ese partido.")
        if match.status == MatchStatus.COMPLETE and match.winner_id != winner_id:
            raise ValueError("No se puede cambiar un partido que ya estaba cerrado con otro ganador.")
        loser_id = next((pid for pid in players if pid != winner_id), None)
        db.update_match_result(conn, match.id, winner_id, loser_id, match.note, match.pledge_done)

    for position in range(1, max(1, len(current_matches) // 2) + 1):
        players = next_slots.get(position, [])
        player_a = players[0] if len(players) >= 1 else None
        player_b = players[1] if len(players) >= 2 else None
        db.set_round_match_players(conn, next_round, position, player_a, player_b)


def render_teams(conn: sqlite3.Connection, names: dict[int, str]) -> None:
    state = db.get_state(conn)
    alive_ids = {match.winner_id for match in db.list_matches(conn, state.current_round) if match.winner_id}
    teams = teams_by_alive_player(conn)
    if not teams:
        st.info("Los bandos aparecen cuando haya representantes.")
        return
    st.caption("Cada bando sigue al representante vivo. Si ese representante pierde, todo su grupo hereda la nueva eleccion.")
    for leader_id in sorted(teams, key=lambda pid: names.get(pid, "")):
        if state.status == TournamentStatus.IN_PROGRESS and leader_id not in alive_ids:
            continue
        members = sorted(teams[leader_id], key=lambda player: player.name)
        st.markdown(f"#### {name_for(names, leader_id)}")
        st.markdown(
            "<div class='team-list'>"
            + "".join(f"<div>{member.name}</div>" for member in members)
            + "</div>",
            unsafe_allow_html=True,
        )


def final_view(conn: sqlite3.Connection) -> None:
    state = db.get_state(conn)
    names = player_name_map(conn)
    champion = name_for(names, state.champion_id)
    hero("Campeon definido", f"{champion} gano el Cumple Mundial.")
    st.balloons()
    if state.champion_id is not None:
        render_team_for_leader(conn, names, state.champion_id, "Bando campeon")


def render_team_for_leader(conn: sqlite3.Connection, names: dict[int, str], leader_id: int, title: str) -> None:
    reps = representative_lookup(conn)
    members = [
        player
        for player in db.list_players(conn)
        if resolve_representative(player.id, reps) == leader_id
    ]
    members.sort(key=lambda player: player.name)
    st.markdown(f"### {title}: {name_for(names, leader_id)}")
    st.markdown(
        "<div class='team-list'>"
        + "".join(f"<div>{member.name}</div>" for member in members)
        + "</div>",
        unsafe_allow_html=True,
    )


def sidebar_admin(conn: sqlite3.Connection) -> None:
    state = db.get_state(conn)
    st.sidebar.title("Cumple Mundial")
    st.sidebar.write(f"Estado: **{state.status.value}**")
    if state.current_round:
        st.sidebar.write(f"Ronda: **{state.current_round}**")
    st.sidebar.write(f"Base: `{Path(db.DB_PATH).name}`")
    st.sidebar.divider()
    st.sidebar.caption("Reinicio total")
    confirm = st.sidebar.text_input("Escribi REINICIAR para borrar todo", key="reset-confirm")
    if st.sidebar.button("Reiniciar torneo", disabled=confirm != "REINICIAR", use_container_width=True):
        db.reset_db(conn)
        st.sidebar.success("Torneo reiniciado")
        rerun()


def main() -> None:
    apply_theme()
    conn = get_connection()
    event_header()
    reset_panel(conn)
    sidebar_admin(conn)
    state = db.get_state(conn)

    if state.status == TournamentStatus.REGISTRATION:
        registration_view(conn)
    elif state.status == TournamentStatus.IN_PROGRESS:
        current_round_view(conn)
    else:
        final_view(conn)


if __name__ == "__main__":
    main()
