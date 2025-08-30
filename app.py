import streamlit as st
from datetime import datetime
from typing import Dict, Any, List

from storage import (
    load_pokedex, load_state, save_state, name_for,
    search_options, parse_number_from_option
)
from ui_components import pairing_tile, fusion_card, graveyard_card

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

    # add each pairing to graveyard if still present
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

    # remove the fusion
    state["fusions"] = [x for x in state["fusions"] if x["id"] != fid]

    # clear any used flags based on remaining fusions
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

def reset_state_confirm():
    if st.button("Reset all state", type="secondary"):
        st.session_state["state"] = {
            "pairings": [],
            "fusions": [],
            "graveyard": [],
            "next_pair_id": 1,
            "next_fusion_id": 1,
            "players": ["Player 1", "Player 2"],
            "version": 1,
        }
        persist()
        st.success("State cleared.")

pokedex = get_pokedex()
state = get_state()
recompute_used_flags()

st.title("Pokémon Infinite Fusion Soullink Tracker")
tabs = st.tabs(["Pairings", "Fusions", "Graveyard", "Settings"])

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
        pairs = [p for p in state["pairings"] if not p.get("dead")]
        if show_only_unfused:
            pairs = [p for p in pairs if not (p["player1"]["used"] or p["player2"]["used"])]
        for i in range(0, len(pairs), 3):
            cols = st.columns(3)
            for j in range(3):
                k = i + j
                if k >= len(pairs):
                    continue
                p = pairs[k]
                with cols[j]:
                    pairing_tile(pokedex, p)
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
        for i in range(0, len(items), 2):
            row = st.columns(2)
            for j in range(2):
                idx = i + j
                if idx >= len(items):
                    continue
                f = items[idx]
                with row[j]:
                    fusion_card(pokedex, f)
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
    st.subheader("Graveyard")
    if not state.get("graveyard"):
        st.info("Graveyard is empty.")
    else:
        for g in list(reversed(state["graveyard"])):
            graveyard_card(pokedex, g)
            if g.get("kind") == "pairing":
                if st.button(f"Delete {g['id']}", key=f"del_grave_{g['id']}"):
                    delete_graveyard_pairing(g['id'])
                    st.rerun()

with tabs[3]:
    st.subheader("Settings")
    reset_state_confirm()
    st.caption("State file: data/state.json")
