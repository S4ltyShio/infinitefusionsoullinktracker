import os
import base64
from functools import lru_cache
import streamlit as st
from typing import Dict, Any
import pandas as pd
from storage import sprite_for, name_for

# ---------- URLs ----------

def ifdex_mon_url(number: int) -> str:
    return f"https://infinitefusiondex.com/details/{int(number)}"

def ifdex_fusion_url(a: int, b: int) -> str:
    return f"https://infinitefusiondex.com/details/{int(a)}.{int(b)}"

def fusion_sprite_url(first_number: int, second_number: int) -> str:
    # Orientation matters: first.second
    return f"https://ifd-spaces.sfo2.cdn.digitaloceanspaces.com/custom/{int(first_number)}.{int(second_number)}.png"

# ---------- HTML image helpers ----------

@lru_cache(maxsize=2048)
def _path_to_data_uri(path: str) -> str:
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""

def _img_src(sprite: str) -> str:
    if not sprite:
        return ""
    s = str(sprite)
    if s.startswith("http://") or s.startswith("https://") or s.startswith("data:"):
        return s
    if os.path.isfile(s):
        return _path_to_data_uri(s)
    return ""

def clickable_sprite(sprite_path_or_url: str, link_url: str, width: int = 96, caption: str | None = None):
    src = _img_src(sprite_path_or_url)
    if not src:
        return
    html = f'<a href="{link_url}" target="_blank"><img src="{src}" width="{width}"></a>'
    st.markdown(html, unsafe_allow_html=True)
    if caption:
        st.caption(caption)

# ---------- UI components ----------

def pokemon_display(df: pd.DataFrame, number: int, caption: str = "", width: int = 96):
    cols = st.columns([1, 2])
    with cols[0]:
        sprite = sprite_for(df, number)
        if sprite:
            clickable_sprite(sprite, ifdex_mon_url(number), width=width)
    with cols[1]:
        nm = name_for(df, number)
        st.markdown(f"**#{int(number):03d} {nm}** · [InfiniteFusionDex]({ifdex_mon_url(number)})")
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
            s1 = sprite_for(df, pairing["player1"]["number"])
            if s1:
                clickable_sprite(s1, ifdex_mon_url(pairing["player1"]["number"]), width=64)
            n1 = int(pairing['player1']['number']); st.caption(f"#{n1:03d} {name_for(df, n1)}")
        with c[1]:
            s2 = sprite_for(df, pairing["player2"]["number"])
            if s2:
                clickable_sprite(s2, ifdex_mon_url(pairing["player2"]["number"]), width=64)
            n2 = int(pairing['player2']['number']); st.caption(f"#{n2:03d} {name_for(df, n2)}")
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

        # Base components: sprite is clickable to InfiniteFusionDex mon page
        c_base = st.columns(4)
        for col, mon in zip(c_base, [a, b, a2, b2]):
            with col:
                spr = sprite_for(df, mon["number"])
                if spr:
                    clickable_sprite(spr, ifdex_mon_url(mon["number"]), width=96)
                st.caption(f"#{int(mon['number']):03d} {mon['name']}")

        st.divider()

        # Fused sprites: clickable to fusion details
        c_fused = st.columns(2)
        with c_fused[0]:
            fused_src = fusion_sprite_url(a["number"], b["number"])
            clickable_sprite(fused_src, ifdex_fusion_url(a["number"], b["number"]), width=144,
                             caption=f"Fused: {a['name']} + {b['name']}")
        with c_fused[1]:
            fused_src2 = fusion_sprite_url(a2["number"], b2["number"])
            clickable_sprite(fused_src2, ifdex_fusion_url(a2["number"], b2["number"]), width=144,
                             caption=f"Fused: {a2['name']} + {b2['name']}")

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
                if s1: st.image(s1, width=72)
                n1 = int(entry['player1']['number']); st.caption(f"#{n1:03d} {name_for(df, n1)}")
            with c[1]:
                s2 = sprite_for(df, entry["player2"]["number"])
                if s2: st.image(s2, width=72)
                n2 = int(entry['player2']['number']); st.caption(f"#{n2:03d} {name_for(df, n2)}")
        else:
            st.write(entry)

def fusion_tile(df: pd.DataFrame, fusion: Dict[str, Any]):
    with st.container(border=True):
        st.markdown(f"**{fusion['id']}**")
        a = fusion["player1"]["a"]; b = fusion["player1"]["b"]
        a2 = fusion["player2"]["a"]; b2 = fusion["player2"]["b"]

        cols = st.columns(2)
        with cols[0]:
            url = fusion_sprite_url(a["number"], b["number"])
            clickable_sprite(url, ifdex_fusion_url(a["number"], b["number"]), width=96,
                             caption=f"{a['name']} + {b['name']}")
        with cols[1]:
            url2 = fusion_sprite_url(a2["number"], b2["number"])
            clickable_sprite(url2, ifdex_fusion_url(a2["number"], b2["number"]), width=96,
                             caption=f"{a2['name']} + {b2['name']}")