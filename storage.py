# storage.py
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
STATE_PATH = DATA_DIR / "state.json"
POKEDEX_CSV = DATA_DIR / "infinite_fusion_pokedex.csv"

# ---------- Pokedex ----------

def _coerce_int_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("Int64")

def _normalize_sprite_path(raw: Optional[str]) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    # URLs pass through
    if s.startswith("http://") or s.startswith("https://") or s.startswith("data:"):
        return s
    # Fix Windows backslashes
    s = s.replace("\\", "/")
    # Make absolute relative to repo
    p = (BASE_DIR / s).resolve()
    if p.is_file():
        return str(p)
    # Fallback: if only a filename was provided, try sprites/<file>
    p2 = (BASE_DIR / "sprites" / Path(s).name).resolve()
    if p2.is_file():
        return str(p2)
    # If not found, return empty so Streamlit won't try to open
    return ""

def load_pokedex(csv_path: Path = POKEDEX_CSV) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Map flexible column names -> canonical
    lower_map = {c.lower(): c for c in df.columns}
    num_col = lower_map.get("number") or lower_map.get("#") or list(df.columns)[0]
    name_col = lower_map.get("name") or list(df.columns)[1]

    # sprite column can be named a few ways
    sprite_col = (
        lower_map.get("sprite")
        or lower_map.get("sprite_path_or_url")
        or lower_map.get("sprite_path")
        or lower_map.get("image")
        or lower_map.get("image_path")
        or None
    )
    # Build a normalized frame
    out = pd.DataFrame(
        {
            "number": _coerce_int_series(df[num_col]),
            "name": df[name_col].astype(str),
        }
    )
    if sprite_col:
        out["sprite"] = df[sprite_col].map(_normalize_sprite_path)
    else:
        out["sprite"] = ""

    return out

# ---------- Lookups ----------

def sprite_for(df: pd.DataFrame, number: int) -> str:
    try:
        n = int(number)
    except Exception:
        return ""
    row = df.loc[df["number"] == n]
    if row.empty:
        return ""
    val = str(row.iloc[0].get("sprite", "")).strip()
    return val

def name_for(df: pd.DataFrame, number: int) -> str:
    try:
        n = int(number)
    except Exception:
        return ""
    row = df.loc[df["number"] == n]
    if row.empty:
        return ""
    return str(row.iloc[0]["name"])

def search_options(df: pd.DataFrame) -> List[str]:
    # e.g., "001 — Bulbasaur"
    opts = [f"{int(n):03d} - {nm}" for n, nm in zip(df["number"].fillna(0), df["name"])]
    return opts

def parse_number_from_option(option: str) -> Optional[int]:
    # Accept "001 - Bulbasaur" or just "001"
    if not option:
        return None
    part = str(option).split("-")[0].strip()
    try:
        return int(part)
    except Exception:
        return None

# ---------- State ----------

def _default_state() -> Dict[str, Any]:
    return {
        "pairings": [],   # list of pairings {id, player1{number,name,used}, player2{...}, dead?}
        "fusions": [],    # list of fusions {id, p1_number, p2_number, ...}
        "graveyard": [],  # list of entries {"kind":"pokemon"/"pairing", ...}
        "created_at": None,
        "updated_at": None,
    }

def load_state() -> Dict[str, Any]:
    try:
        if STATE_PATH.is_file():
            with STATE_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    # Ensure directory exists for later saves
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _default_state()

def save_state(state: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(STATE_PATH)

# ---------- External links ----------

def _slugify_name(name: str) -> str:
    import re, unicodedata
    n = str(name).lower()
    n = (
        n.replace("♀", "-f")
        .replace("♂", "-m")
        .replace(".", "")
        .replace("'", "")
        .replace(":", "")
    )
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii")
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    return n

def pokemondb_url(name: str) -> str:
    return f"https://pokemondb.net/pokedex/{_slugify_name(name)}"


def _colmap(df):
    return {c.lower(): c for c in df.columns}

def get_evolutions(df: pd.DataFrame, number: int):
    """Return list of (num:int, name:str) next evolutions based on CSV columns
    'evolves_to_numbers' and 'evolves_to_names'."""
    row = df.loc[df["number"] == number]
    if row.empty:
        return []
    cols = _colmap(df)
    num_col = cols.get("evolves_to_numbers")
    name_col = cols.get("evolves_to_names")
    if not num_col or num_col not in df.columns:
        return []
    raw = row.iloc[0][num_col]
    nums_raw = str(raw) if pd.notna(raw) else ""
    if not nums_raw.strip():
        return []
    parts = [p.strip() for p in nums_raw.split("|")]
    out_nums = []
    for p in parts:
        try:
            out_nums.append(int(p))
        except ValueError:
            try:
                out_nums.append(int(p.lstrip("0") or "0"))
            except Exception:
                pass
    names = []
    if name_col and name_col in df.columns:
        rawn = row.iloc[0][name_col]
        partsn = [p.strip() for p in str(rawn).split("|")] if pd.notna(rawn) else []
        for i, n in enumerate(out_nums):
            if i < len(partsn) and partsn[i]:
                names.append(partsn[i])
            else:
                names.append(name_for(df, n))
    else:
        names = [name_for(df, n) for n in out_nums]
    return list(zip(out_nums, names))
