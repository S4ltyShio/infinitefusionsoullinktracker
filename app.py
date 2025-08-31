import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Tuple
import pandas as pd

from storage import (
    load_pokedex, load_state, save_state, name_for,
    search_options, parse_number_from_option, get_evolutions
)
from ui_components import pairing_tile, fusion_tile, graveyard_card, team_pokemon_card

st.set_page_config(page_title="Soullink Fusion Tracker", page_icon="🧬", layout="wide")

@st.cache_data
def get_pokedex():
    return load_pokedex()

def get_state() -> Dict[str, Any]:
    if "state" not in st.session_state:
        st.session_state["state"] = load_state()
    st.session_state["state"].setdefault("graveyard", [])
    st.session_state["state"].setdefault("pairings", [])
    st.session_state["state"].setdefault("fusions", [])
    st.session_state["state"].setdefault("player1_team", [])
    st.session_state["state"].setdefault("player2_team", [])
    st.session_state["state"].setdefault("next_pair_id", 1)
    st.session_state["state"].setdefault("next_fusion_id", 1)
    return st.session_state["state"]

def persist():
    save_state(st.session_state["state"])

def add_pairing(p1_number: int, encounter: str, p2_number: int):
    state = get_state()
    pid = state["next_pair_id"]
    pairing = {
        "id": f"P{pid:04d}",
        "created_at": datetime.utcnow().isoformat(),
        "player1": {"number": int(p1_number), "name": name_for(pokedex, p1_number), "encounter": encounter, "used": False},
        "player2": {"number": int(p2_number), "name": name_for(pokedex, p2_number), "encounter": encounter, "used": False},
    }
    state["pairings"].append(pairing)
    state["next_pair_id"] += 1
    persist()

def available_player_pokemon(player_idx: int) -> List[Dict[str, Any]]:
    key = "player1" if player_idx == 0 else "player2"
    return [
        {"pairing_id": p["id"], "number": p[key]["number"], "name": p[key]["name"]}
        for p in get_state()["pairings"]
        if not p.get("dead") and not p[key]["used"]
    ]

def get_all_player_pokemon(player_idx: int) -> List[Dict[str, Any]]:
    player_key = "player1" if player_idx == 0 else "player2"
    all_pokemon = []
    
    # From pairings (unfused and available)
    for p in get_state()["pairings"]:
        if not p.get("dead") and not p[player_key]["used"]:
            mon = p[player_key].copy()
            mon["pairing_id"] = p["id"]
            mon["source"] = "Paired"
            mon["uid"] = f'{p["id"]}_{player_key}'
            all_pokemon.append(mon)
            
    # From fusions
    for f in get_state()["fusions"]:
        fused_mon_data = f[player_key]
        mon = {
            "source": "Fusion",
            "fusion_id": f["id"],
            "uid": f'{f["id"]}_{player_key}',
            "name": f"{fused_mon_data['a']['name']} / {fused_mon_data['b']['name']}",
            "number_a": fused_mon_data['a']['number'],
            "number_b": fused_mon_data['b']['number'],
        }
        all_pokemon.append(mon)
        
    return all_pokemon

def create_fusion_from_player1(p1_pair_id_a: str, p1_pair_id_b: str):
    state = get_state()
    if p1_pair_id_a == p1_pair_id_b:
        st.error("Choose two different pairings.")
        return
    pa = next((p for p in state["pairings"] if p["id"] == p1_pair_id_a), None)
    pb = next((p for p in state["pairings"] if p["id"] == p1_pair_id_b), None)
    if not pa or not pb:
        st.error("Pairing not found.")
        return
    if pa.get("dead") or pb.get("dead"):
        st.error("Selected pairing is in graveyard.")
        return
    if pa["player1"]["used"] or pb["player1"]["used"]:
        st.error("Selected Player 1 Pokémon already fused.")
        return
    if pa["player2"]["used"] or pb["player2"]["used"]:
        st.error("Linked Player 2 Pokémon already fused.")
        return

    fid = state["next_fusion_id"]
    fusion = {
        "id": f"F{fid:04d}",
        "created_at": datetime.utcnow().isoformat(),
        "player1": {
            "a": {"pairing_id": pa["id"], "number": pa["player1"]["number"], "name": pa["player1"]["name"]},
            "b": {"pairing_id": pb["id"], "number": pb["player1"]["number"], "name": pb["player1"]["name"]},
        },
        "player2": {
            "a": {"pairing_id": pa["id"], "number": pa["player2"]["number"], "name": pa["player2"]["name"]},
            "b": {"pairing_id": pb["id"], "number": pb["player2"]["number"], "name": pb["player2"]["name"]},
        },
    }
    for side in ("player1", "player2"):
        pa[side]["used"] = True
        pb[side]["used"] = True

    state["fusions"].append(fusion)
    state["next_fusion_id"] += 1
    persist()
    st.success(f"Created fusion {fusion['id']}")

def recompute_used_flags():
    state = get_state()
    for p in state["pairings"]:
        dead = bool(p.get("dead"))
        p["player1"]["used"] = dead
        p["player2"]["used"] = dead
    pair_by_id = {p["id"]: p for p in state["pairings"]}
    for f in state["fusions"]:
        for side in ("player1", "player2"):
            for slot in ("a", "b"):
                pid = f[side][slot]["pairing_id"]
                if pid in pair_by_id:
                    pair_by_id[pid][side]["used"] = True
    persist()

def unfuse_fusion(fid: str):
    state = get_state()
    before = len(state["fusions"])
    state["fusions"] = [f for f in state["fusions"] if f["id"] != fid]
    if len(state["fusions"]) == before:
        st.error("Fusion not found.")
        return
    recompute_used_flags()
    persist()
    st.success(f"Unfused {fid}")

def send_pairing_to_graveyard(pid: str):
    state = get_state()
    p = next((x for x in state["pairings"] if x["id"] == pid), None)
    if not p:
        st.error("Pairing not found.")
        return
    if p["player1"]["used"] or p["player2"]["used"]:
        st.error("Cannot send to graveyard. Pairing is in a fusion.")
        return
    state["graveyard"].append({
        "kind": "pairing",
        "id": pid,
        "player1": {"number": p["player1"]["number"]},
        "player2": {"number": p["player2"]["number"]},
        "created_at": datetime.utcnow().isoformat(),
    })
    state["pairings"] = [x for x in state["pairings"] if x["id"] != pid]
    persist()
    st.success(f"Sent pairing {pid} to graveyard.")

def bury_fusion(fid: str):
    """Remove fusion and move both involved pairings to graveyard as 'pairing' entries."""
    state = get_state()
    f = next((x for x in state["fusions"] if x["id"] == fid), None)
    if not f:
        st.error("Fusion not found.")
        return

    pid_a = f["player1"]["a"]["pairing_id"]
    pid_b = f["player1"]["b"]["pairing_id"]
    pair_ids = [pid_a, pid_b]

    now = datetime.utcnow().isoformat()
    new_graves = []
    keep_pairings = []
    for p in state["pairings"]:
        if p["id"] in pair_ids:
            state["graveyard"].append({
                "kind": "pairing",
                "id": p["id"],
                "player1": {"number": p["player1"]["number"]},
                "player2": {"number": p["player2"]["number"]},
                "created_at": now,
            })
            new_graves.append(p["id"])
        else:
            keep_pairings.append(p)
    state["pairings"] = keep_pairings
    state["fusions"] = [x for x in state["fusions"] if x["id"] != fid]

    recompute_used_flags()
    persist()
    if new_graves:
        st.success(f"send {fid} to graveyard: sent pairings {', '.join(new_graves)} to graveyard.")
    else:
        st.success(f"send {fid} to graveyard: fusion removed. No pairings found to bury.")

def delete_pairing(pid: str):
    state = get_state()
    p = next((x for x in state["pairings"] if x["id"] == pid), None)
    if not p:
        st.error("Pairing not found.")
        return
    if p["player1"]["used"] or p["player2"]["used"]:
        st.error("Cannot delete. Pairing is in a fusion. Unfuse or bury the fusion first.")
        return
    state["pairings"] = [x for x in state["pairings"] if x["id"] != pid]
    persist()
    st.success(f"Deleted pairing {pid}")

def delete_graveyard_pairing(pid: str):
    state = get_state()
    before = len(state["graveyard"])
    state["graveyard"] = [
        g for g in state["graveyard"]
        if not (g.get("kind") == "pairing" and g.get("id") == pid)
    ]
    if len(state["graveyard"]) == before:
        st.error("Graveyard pairing not found.")
        return
    persist()
    st.success(f"Deleted graveyard pairing {pid}")

# ---------------- Evolution helpers ----------------

def _update_fusions_for_pairing(pid: str, evolved_side: str, new_number: int, new_name: str):
    """Propagate evolved species into any fusion entries that reference this pairing.
    evolved_side is 'player1' or 'player2' and updates only the matching side in fusions.
    """
    state = get_state()
    for f in state["fusions"]:
        for side in ("player1", "player2"):
            for slot in ("a", "b"):
                if f[side][slot]["pairing_id"] == pid:
                    # Update the numbers/names only on the side that evolved
                    if side == evolved_side:
                        f[side][slot]["number"] = int(new_number)
                        f[side][slot]["name"] = new_name

def evolve_pairing_mon(pid: str, side: str, new_number: int):
    """side: 'player1' or 'player2'."""
    state = get_state()
    p = next((x for x in state["pairings"] if x["id"] == pid), None)
    if not p:
        st.error("Pairing not found.")
        return
    # Prevent evolving buried mons, but allow evolving while fused
    if p.get("dead"):
        st.error("Cannot evolve. Pairing is in graveyard.")
        return

    p[side]["number"] = int(new_number)
    p[side]["name"] = name_for(pokedex, new_number)

    _update_fusions_for_pairing(pid, side, int(new_number), p[side]["name"])
    persist()
    st.success(f"Evolved {pid} {side} to #{int(new_number):03d} {p[side]['name']}")

def evolution_controls(pid: str, side: str, current_number: int, key_prefix: str = ""):
    """Inline UI for evolving a single Pokémon."""
    evos: List[Tuple[int, str]] = get_evolutions(pokedex, int(current_number))
    if not evos:
        st.caption("No evolutions available")
        return

    if len(evos) == 1:
        n, nm = evos[0]
        if st.button(f"Evolve {side[-1]} → #{n:03d}", key=f"{key_prefix}evolve_one_{pid}_{side}"):
            evolve_pairing_mon(pid, side, n)
            st.rerun()
        return

    # Multiple evolutions: choose then confirm
    labels = [f"{n:03d} - {nm}" for n, nm in evos]
    sel = st.selectbox(
        f"Evolve {side[-1]}",
        labels,
        key=f"{key_prefix}evo_sel_{pid}_{side}",
        index=None,
        placeholder="Choose evolution",
    )
    if st.button("Confirm evolve", key=f"{key_prefix}evo_confirm_{pid}_{side}", disabled=sel is None):
        idx = labels.index(sel)
        n, _ = evos[idx]
        evolve_pairing_mon(pid, side, n)
        st.rerun()

def reset_state_confirm():
    if st.button("Reset all state", type="secondary"):
        st.session_state["state"] = {
            "pairings": [],
            "fusions": [],
            "graveyard": [],
            "player1_team": [],
            "player2_team": [],
            "next_pair_id": 1,
            "next_fusion_id": 1,
            "players": ["Player 1", "Player 2"],
            "version": 1,
        }
        persist()
        st.success("State cleared.")

# ---------------- Team UI ----------------

def team_management_ui(player_idx: int, pokedex_df: pd.DataFrame):
    player_name = f"Player {player_idx + 1}"
    team_key = f"player{player_idx + 1}_team"
    state = get_state()
    
    st.subheader(f"{player_name}'s Team")

    # --- Selection ---
    available_mons = get_all_player_pokemon(player_idx)
    team_uids = {mon['uid'] for mon in state[team_key]}
    selectable_mons = [m for m in available_mons if m['uid'] not in team_uids]
    
    # Create display labels for the selectbox
    options = {}
    for p in selectable_mons:
        if p.get('source') == 'Fusion':
            label = f"{p['name']} (Fusion {p['fusion_id']})"
        else: # Paired
            label = f"#{p['number']:03d} {p['name']} (Pairing {p['pairing_id']})"
        options[label] = p

    if len(state[team_key]) >= 6:
        st.warning("Team is full.")
    else:
        selected_label = st.selectbox(
            f"Add Pokémon to {player_name}'s team",
            options.keys(),
            key=f"team_select_p{player_idx}",
            index=None,
            placeholder="Choose a Pokémon..."
        )

        if st.button(f"Add to {player_name}'s Team", key=f"team_add_p{player_idx}", disabled=not selected_label):
            selected_pokemon = options[selected_label]
            source = selected_pokemon.get("source")

            # --- Logic for adding a FUSION to the team ---
            if source == "Fusion":
                fusion_id = selected_pokemon.get('fusion_id')
                fusion = next((f for f in get_state()['fusions'] if f['id'] == fusion_id), None)
                if fusion:
                    state[team_key].append(selected_pokemon) # Add to current player's team

                    # Construct and add the other player's fusion
                    other_player_idx = 1 - player_idx
                    other_team_key = f"player{other_player_idx + 1}_team"
                    other_player_key = "player1" if other_player_idx == 0 else "player2"
                    
                    other_fused_data = fusion[other_player_key]
                    other_fusion_mon = {
                        "source": "Fusion",
                        "fusion_id": fusion["id"],
                        "uid": f'{fusion["id"]}_{other_player_key}',
                        "name": f"{other_fused_data['a']['name']} / {other_fused_data['b']['name']}",
                        "number_a": other_fused_data['a']['number'],
                        "number_b": other_fused_data['b']['number'],
                    }
                    
                    other_team_uids = {mon['uid'] for mon in state[other_team_key]}
                    if len(state[other_team_key]) < 6 and other_fusion_mon['uid'] not in other_team_uids:
                        state[other_team_key].append(other_fusion_mon)
                    
                    persist()
                    st.rerun()
                else:
                    st.error("Could not find the associated fusion.")
            
            # --- Logic for adding a PAIRED mon to the team (existing logic) ---
            else: 
                pairing_id = selected_pokemon.get('pairing_id')
                pairing = next((p for p in get_state()['pairings'] if p['id'] == pairing_id), None)
                if pairing:
                    state[team_key].append(selected_pokemon)

                    other_player_idx = 1 - player_idx
                    other_team_key = f"player{other_player_idx + 1}_team"
                    other_player_key = "player1" if other_player_idx == 0 else "player2"
                    other_pokemon = pairing[other_player_key].copy()
                    other_pokemon["pairing_id"] = pairing["id"]
                    other_pokemon["source"] = "Paired"
                    other_pokemon["uid"] = f'{pairing["id"]}_{other_player_key}'
                    
                    other_team_uids = {mon['uid'] for mon in state[other_team_key]}
                    if len(state[other_team_key]) < 6 and other_pokemon['uid'] not in other_team_uids:
                        state[other_team_key].append(other_pokemon)
                    persist()
                    st.rerun()
                else:
                    st.error("Could not find the associated pairing.")

    st.divider()

    # --- Display Team ---
    if not state[team_key]:
        st.info(f"{player_name} has no Pokémon in their team yet.")
    else:
        for i in range(0, 6, 2):
            cols = st.columns(2)
            for j in range(2):
                idx = i + j
                if idx < len(state[team_key]):
                    with cols[j]:
                        pokemon = state[team_key][idx]
                        team_pokemon_card(pokedex_df, pokemon)

                        # --- Evolution Controls (only for paired) ---
                        if pokemon.get('source', 'Paired') == 'Paired':
                            pokemon_pairing_id = pokemon.get('pairing_id')
                            pokemon_uid = pokemon.get('uid')
                            if pokemon_pairing_id and pokemon_uid:
                                side = pokemon_uid.split('_')[-1]
                                number = pokemon.get('number')
                                if side in ('player1', 'player2') and number is not None:
                                    evolution_controls(
                                        pokemon_pairing_id, side, number, 
                                        key_prefix=f"team_{pokemon_uid}_"
                                    )

                        # --- Remove Button (handles both types) ---
                        if st.button("Remove", key=f"remove_p{player_idx}_{pokemon['uid']}"):
                            uid_to_remove = pokemon.get('uid')
                            state[team_key] = [p for p in state[team_key] if p.get('uid') != uid_to_remove]

                            other_player_idx = 1 - player_idx
                            other_team_key = f"player{other_player_idx + 1}_team"
                            current_player_key = uid_to_remove.split('_')[-1]
                            other_player_key = 'player2' if current_player_key == 'player1' else 'player1'
                            
                            id_part = uid_to_remove.split('_')[0]
                            paired_uid_to_remove = f"{id_part}_{other_player_key}"
                            state[other_team_key] = [p for p in state[other_team_key] if p.get('uid') != paired_uid_to_remove]

                            persist()
                            st.rerun()


# ---------------- App ----------------

pokedex = get_pokedex()
state = get_state()
recompute_used_flags()

st.title("Pokémon Infinite Fusion Soullink Tracker")
tabs = st.tabs(["Pairings", "Fusions", "Team", "Graveyard", "Settings"])

with tabs[0]:
    st.subheader("Add a new pairing")
    col_add = st.columns(2)
    options = search_options(pokedex)
    with col_add[0]:
        p1_opt = st.selectbox("Player 1 Pokémon", options, key="p1_select", index=None, placeholder="Search species...")
    with col_add[1]:
        p2_opt = st.selectbox("Player 2 Pokémon", options, key="p2_select", index=None, placeholder="Search species...")
    encounter = st.text_input("Encounter", placeholder="e.g., Route 1, Cave, Gift")

    can_add = p1_opt and p2_opt and encounter.strip()
    if st.button("Add pairing", type="primary", disabled=not can_add):
        p1_num = parse_number_from_option(p1_opt)
        p2_num = parse_number_from_option(p2_opt)
        if p1_num is None or p2_num is None:
            st.error("Failed to parse Pokémon number from selection.")
        else:
            add_pairing(p1_num, encounter.strip(), p2_num)
            st.rerun()

    st.divider()
    
    st.subheader("Current pairings")
    if not state["pairings"]:
        st.info("No pairings yet.")
    else:
        show_only_unfused = st.checkbox("Show only unfused", value=False)
        search_q = st.text_input("Search pairings", key="pairings_search", placeholder="ID, name, number, or encounter")
        pairs = [p for p in state["pairings"] if not p.get("dead")]
        if show_only_unfused:
            pairs = [p for p in pairs if not (p["player1"]["used"] or p["player2"]["used"])]
        if search_q:
            q = search_q.strip().lower()
            def _pmatch(p):
                fields = [
                    p.get("id",""),
                    p["player1"].get("name",""), p["player2"].get("name",""),
                    f"{int(p['player1']['number']):03d}", f"{int(p['player2']['number']):03d}",
                    str(p["player1"].get("encounter","")), str(p["player2"].get("encounter",""))
                ]
                return any(q in str(x).lower() for x in fields)
            pairs = [p for p in pairs if _pmatch(p)]

        for i in range(0, len(pairs), 6):
            cols = st.columns(6)
            for j in range(6):
                k = i + j
                if k >= len(pairs):
                    continue
                p = pairs[k]
                with cols[j]:
                    pairing_tile(pokedex, p)

                    # evolve controls for Player 1 and Player 2
                    evo_cols = st.columns(2)
                    with evo_cols[0]:
                        evolution_controls(p["id"], "player1", p["player1"]["number"])
                    with evo_cols[1]:
                        evolution_controls(p["id"], "player2", p["player2"]["number"])

                    disabled = p["player1"]["used"] or p["player2"]["used"]
                    btns = st.columns(2)
                    with btns[0]:
                        if st.button(f"Send {p['id']} to graveyard", key=f"grave_{p['id']}", disabled=disabled):
                            send_pairing_to_graveyard(p['id'])
                            st.rerun()
                    with btns[1]:
                        if st.button(f"Delete {p['id']}", key=f"del_{p['id']}", disabled=disabled):
                            delete_pairing(p['id'])
                            st.rerun()

with tabs[1]:
    st.subheader("Create a fusion")
    avail_p1 = [
        (item["pairing_id"], f"{item['pairing_id']} — #{int(item['number']):03d} {item['name']}")
        for item in available_player_pokemon(0)
    ]
    colf = st.columns(2)
    with colf[0]:
        sel_a = st.selectbox("Select first Pokémon (Player 1)", [label for _, label in avail_p1], index=None, placeholder="Choose...")
    with colf[1]:
        sel_b = st.selectbox("Select second Pokémon (Player 1)", [label for _, label in avail_p1], index=None, placeholder="Choose...")

    def label_to_pairing_id(label: str) -> str:
        return label.split(" — ")[0] if label else None

    if st.button("Create fusion", type="primary", disabled=not (sel_a and sel_b)):
        id_a = label_to_pairing_id(sel_a)
        id_b = label_to_pairing_id(sel_b)
        create_fusion_from_player1(id_a, id_b)
        st.rerun()

    st.divider()
    
    st.subheader("Fusions")
    if not state["fusions"]:
        st.info("No fusions yet.")
    else:
        items = list(state["fusions"])
        search_f = st.text_input("Search fusions", key="fusions_search", placeholder="ID or Pokémon names")
        if search_f:
            qf = search_f.strip().lower()
            def _fmatch(f):
                names = [
                    f["id"],
                    f["player1"]["a"]["name"], f["player1"]["b"]["name"],
                    f["player2"]["a"]["name"], f["player2"]["b"]["name"],
                    f"{int(f['player1']['a']['number']):03d}", f"{int(f['player1']['b']['number']):03d}",
                    f"{int(f['player2']['a']['number']):03d}", f"{int(f['player2']['b']['number']):03d}",
                ]
                return any(qf in str(x).lower() for x in names)
            items = [f for f in items if _fmatch(f)]

        for i in range(0, len(items), 6):
            row = st.columns(6)
            for j in range(6):
                idx = i + j
                if idx >= len(items):
                    continue
                f = items[idx]
                with row[j]:
                    fusion_tile(pokedex, f)
                    btns = st.columns(2)
                    with btns[0]:
                        if st.button(f"Unfuse {f['id']}", key=f"unfuse_{f['id']}"):
                            unfuse_fusion(f['id'])
                            st.rerun()
                    with btns[1]:
                        if st.button(f"Send {f['id']} to graveyard", key=f"bury_{f['id']}"):
                            bury_fusion(f['id'])
                            st.rerun()

with tabs[2]:
    st.subheader("Current Team")
    main_cols = st.columns(2)
    with main_cols[0]:
        team_management_ui(0, pokedex)
    with main_cols[1]:
        team_management_ui(1, pokedex)

with tabs[3]:
    st.subheader("Graveyard")
    if not state.get("graveyard"):
        st.info("Graveyard is empty.")
    else:
        grave_items = list(reversed(state["graveyard"]))
        search_g = st.text_input("Search graveyard", key="grave_search", placeholder="ID, name, or number")
        if search_g:
            qg = search_g.strip().lower()
            def _gmatch(g):
                if g.get("kind") == "pairing":
                    n1 = int(g["player1"]["number"]); n2 = int(g["player2"]["number"])
                    fields = [g.get("id",""), f"{n1:03d}", f"{n2:03d}"]
                    fields += [name_for(pokedex, n1), name_for(pokedex, n2)]
                    return any(qg in str(x).lower() for x in fields)
                return False
            grave_items = [g for g in grave_items if _gmatch(g)]

        for i in range(0, len(grave_items), 6):
            cols = st.columns(6)
            for j in range(6):
                k = i + j
                if k >= len(grave_items):
                    continue
                g = grave_items[k]
                with cols[j]:
                    graveyard_card(pokedex, g)
                    if g.get("kind") == "pairing":
                        if st.button(f"Delete {g['id']}", key=f"del_grave_{g['id']}"):
                            delete_graveyard_pairing(g['id'])
                            st.rerun()

with tabs[4]:
    st.subheader("Settings")
    reset_state_confirm()
    st.caption("State file: data/state.json")

