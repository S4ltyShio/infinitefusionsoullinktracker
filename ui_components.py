import streamlit as st
from typing import Dict, Any
import pandas as pd
from storage import sprite_for, name_for, pokemondb_url

def fusion_sprite_url(first_number: int, second_number: int) -> str:
    # Orientation matters: first.second
    return f"https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/custom/{int(first_number)}.{int(second_number)}.png"

def pokemon_display(df: pd.DataFrame, number: int, caption: str = "", width: int = 96):
    cols = st.columns([1, 2])
    with cols[0]:
        sprite = sprite_for(df, number)
        if sprite:
            st.image(sprite, width=width)
    with cols[1]:
        nm = name_for(df, number)
        st.markdown(f"**#{int(number):03d} {nm}** · [PokémonDB]({pokemondb_url(nm)})")
        if caption:
            st.caption(caption)

def pairing_card(df: pd.DataFrame, pairing: Dict[str, Any]):
    with st.container(border=True):
        cols = st.columns(2)
        with cols[0]:
            p1 = pairing["player1"]
            pokemon_display(df, p1["number"], caption=f'{p1.get("encounter","")}', width=96)
            st.caption("Player 1")
            st.caption("Fused" if p1.get("used") else "Unfused")
        with cols[1]:
            p2 = pairing["player2"]
            pokemon_display(df, p2["number"], caption=f'{p2.get("encounter","")}', width=96)
            st.caption("Player 2")
            st.caption("Fused" if p2.get("used") else "Unfused")

def pairing_tile(df: pd.DataFrame, pairing: Dict[str, Any]):
    with st.container(border=True):
        c = st.columns([1, 1])
        with c[0]:
            s = sprite_for(df, pairing["player1"]["number"])
            if s:
                st.image(s, width=64)
            st.caption(f"#{int(pairing['player1']['number']):03d}")
        with c[1]:
            s2 = sprite_for(df, pairing["player2"]["number"])
            if s2:
                st.image(s2, width=64)
            st.caption(f"#{int(pairing['player2']['number']):03d}")
        enc = pairing["player1"].get("encounter") or pairing["player2"].get("encounter") or ""
        if enc:
            st.caption(enc)
        p1u = "Fused" if pairing["player1"].get("used") else "Unfused"
        p2u = "Fused" if pairing["player2"].get("used") else "Unfused"
        st.caption(f"P1: {p1u} · P2: {p2u}")

def fusion_card(df: pd.DataFrame, fusion: Dict[str, Any]):
    with st.container(border=True):
        st.markdown(f"**Fusion {fusion['id']}**")

        a = fusion["player1"]["a"]
        b = fusion["player1"]["b"]
        a2 = fusion["player2"]["a"]
        b2 = fusion["player2"]["b"]

        # Base components with single-mon Dex links
        c_base = st.columns(4)
        for col, mon in zip(c_base, [a, b, a2, b2]):
            with col:
                spr = sprite_for(df, mon["number"])
                if spr:
                    st.image(spr, width=96)
                st.caption(f"#{int(mon['number']):03d} {mon['name']}")
                st.markdown(f"[Dex](https://infinitefusiondex.com/details/{int(mon['number'])})")

        st.divider()

        # Fused sprites for both players with fusion details links
        c_fused = st.columns(2)
        with c_fused[0]:
            url = fusion_sprite_url(a["number"], b["number"])
            st.image(url, width=144)
            st.caption(f"Fused: {a['name']} + {b['name']}")
            st.markdown(f"[Details](https://infinitefusiondex.com/details/{int(a['number'])}.{int(b['number'])})")
        with c_fused[1]:
            url2 = fusion_sprite_url(a2["number"], b2["number"])
            st.image(url2, width=144)
            st.caption(f"Fused: {a2['name']} + {b2['name']}")
            st.markdown(f"[Details](https://infinitefusiondex.com/details/{int(a2['number'])}.{int(b2['number'])})")

def graveyard_card(df: pd.DataFrame, entry: Dict[str, Any]):
    kind = entry.get("kind")
    with st.container(border=True):
        if kind == "fusion":
            st.markdown(f"**Grave: Fusion {entry.get('id','')}**")
            cols = st.columns(2)
            with cols[0]:
                a = int(entry["player1"]["a_num"])
                b = int(entry["player1"]["b_num"])
                row = st.columns([1, 1, 1.2])
                with row[0]:
                    s = sprite_for(df, a)
                    if s: st.image(s, width=64)
                    st.caption(f"#{a:03d}")
                with row[1]:
                    s = sprite_for(df, b)
                    if s: st.image(s, width=64)
                    st.caption(f"#{b:03d}")
                with row[2]:
                    url = fusion_sprite_url(a, b)
                    st.image(url, width=112)
                    st.caption("fused")
            with cols[1]:
                a2 = int(entry["player2"]["a_num"])
                b2 = int(entry["player2"]["b_num"])
                row2 = st.columns([1, 1, 1.2])
                with row2[0]:
                    s = sprite_for(df, a2)
                    if s: st.image(s, width=64)
                    st.caption(f"#{a2:03d}")
                with row2[1]:
                    s = sprite_for(df, b2)
                    if s: st.image(s, width=64)
                    st.caption(f"#{b2:03d}")
                with row2[2]:
                    url2 = fusion_sprite_url(a2, b2)
                    st.image(url2, width=112)
                    st.caption("fused")
        elif kind == "pairing":
            st.markdown(f"**Grave: Pairing {entry.get('id','')}**")
            c = st.columns(2)
            with c[0]:
                s1 = sprite_for(df, entry["player1"]["number"])
                if s1: st.image(s1, width=96)
                st.caption(f"#{int(entry['player1']['number']):03d}")
            with c[1]:
                s2 = sprite_for(df, entry["player2"]["number"])
                if s2: st.image(s2, width=96)
                st.caption(f"#{int(entry['player2']['number']):03d}")
        else:
            st.write(entry)
