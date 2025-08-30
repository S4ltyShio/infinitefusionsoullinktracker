# storage.py
import json
import os
import time
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
    # Pass through URLs and data URIs
    if s.startswith(("http://", "https://", "data:")):
        return s
    # Normalize slashes for cross-platform use
    s = s.replace("\\", "/")
    # Try path as given, relative to repo
    p = (BASE_DIR / s).resolve()
    if p.is_file():
        return str(p)
    # Fallback: look in sprites/ by filename
    p2 = (BASE_DIR / "sprites" / Path(s).name).resolve()
    if p2.is_file():
        return str(p2)
    return ""

def load_pokedex(csv_path: Path = POKEDEX_CSV) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Flexible column detection
    lower_map = {c.lower(): c for c in df.columns}
    num_col = lower_map.get("number") or lower_map.get("#") or list(df.columns)[0]
    name_col = lower_map.get("name") or list(df.columns)[1]
    sprite_col = (
        lower_map.get("sprite")
        or lower_map.get("sprite_path_or_url")
        or lower_map.get("sprite_path")
        or lower_map.get("image")
        or lower_map.get("image_path")
        or None
    )

    out = pd.DataFrame(
        {
            "number": _coerce_int_series(df[num_col]),
            "name": df[name_col].astype(str),
        }
    )
    out["sprite"] = df[sprite_col].map(_normalize_sprite_path) if sprite_col else ""
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
    return str(row.iloc[0].get("sprite", "")).strip()

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
    return [f"{int(n):03d} - {nm}" for n, nm in zip(df["number"].fillna(0), df["name"])]

def parse_number_from_option(option: str) -> Optional[int]:
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
        "pairings": [],
        "fusions": [],
        "graveyard": [],
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
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _default_state()

def save_state(state: Dict[str, Any]) -> None:
    """
    Cross-platform safe save.
    1) Write to temp file.
    2) Atomically replace target via os.replace().
    3) Retry on PermissionError (Windows file locks).
    4) Fallback to direct write if needed.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")

    # Write temp
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # Atomic replace with retries
    for attempt in range(6):
        try:
            os.replace(tmp, STATE_PATH)  # atomic on Linux and Windows
            return
        except PermissionError:
            time.sleep(0.25 * (attempt + 1))
        except Exception:
            break

    # Fallback direct write
    try:
        with STATE_PATH.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass

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
    """Read evolutions from optional CSV columns:
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
    out_nums: List[int] = []
    for p in parts:
        try:
            out_nums.append(int(p))
        except ValueError:
            try:
                out_nums.append(int(p.lstrip("0") or "0"))
            except Exception:
                pass
    names: List[str] = []
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
