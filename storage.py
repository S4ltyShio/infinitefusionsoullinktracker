import json
from pathlib import Path
import pandas as pd
from typing import Dict, Any, List

DATA_DIR = Path(__file__).parent / "data"
STATE_PATH = DATA_DIR / "state.json"
POKEDEX_CSV = DATA_DIR / "infinite_fusion_pokedex.csv"

def load_pokedex(csv_path: Path = POKEDEX_CSV) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # Normalize column names
    cols = {c.lower(): c for c in df.columns}
    for required in ["number", "name", "sprite_path_or_url"]:
        if required not in [c.lower() for c in df.columns]:
            raise ValueError(f"CSV missing required column: {required}")
    # Re-map to consistent names
    df = df.rename(columns={cols.get("number"): "number",
                            cols.get("name"): "name",
                            cols.get("sprite_path_or_url"): "sprite"})
    # Ensure types
    try:
        df["number"] = df["number"].astype(int)
    except Exception:
        # If numbers like '001', coerce
        df["number"] = pd.to_numeric(df["number"], errors="coerce").astype("Int64")
    return df

def initial_state() -> Dict[str, Any]:
    return {
        "pairings": [],   # list of pairing dicts
        "fusions": [],
        "graveyard": [],    # list of fusion dicts
        "next_pair_id": 1,
        "next_fusion_id": 1,
        "players": ["Player 1", "Player 2"],
        # for forward compatibility
        "version": 1,
    }

def load_state() -> Dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            # Fall back to fresh state if file corrupted
            return initial_state()
    return initial_state()

def save_state(state: Dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def sprite_for(df: pd.DataFrame, number: int) -> str:
    row = df.loc[df["number"] == number]
    if row.empty:
        return ""
    return str(row.iloc[0]["sprite"])

def name_for(df: pd.DataFrame, number: int) -> str:
    row = df.loc[df["number"] == number]
    if row.empty:
        return f"#{number}"
    return str(row.iloc[0]["name"])

def search_options(df: pd.DataFrame) -> List[str]:
    # Format: '#001 Bulbasaur'
    def fmt(row):
        num = row["number"]
        nm = row["name"]
        if pd.notna(num):
            return f"#{int(num):03d} {nm}"
        else:
            return f"{nm}"
    return [fmt(r) for _, r in df.iterrows()]

def parse_number_from_option(option: str) -> int:
    # Option format '#001 Bulbasaur'
    try:
        if option.startswith("#") and " " in option:
            return int(option[1:4])
    except Exception:
        pass
    # Fallback: no-op
    return None


def _slugify_name(name: str) -> str:
    import re, unicodedata
    n = name.lower()
    # Replace gender symbols
    n = n.replace('♀', '-f').replace('♂', '-m').replace('.', '').replace("'", '').replace(':','')
    # Normalize accents
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode('ascii')
    # Replace spaces and non alphanum with hyphen
    n = re.sub(r'[^a-z0-9]+', '-', n).strip('-')
    return n

def pokemondb_url(name: str) -> str:
    slug = _slugify_name(name)
    return f"https://pokemondb.net/pokedex/{slug}"
