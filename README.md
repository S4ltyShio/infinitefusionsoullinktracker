# Pokémon Infinite Fusion Soullink Tracker

Two-tab Streamlit app:
- **Pairings:** add and manage Soullink pairings between two players' encounters.
- **Fusions:** fuse two of Player 1's unfused Pokémon; Player 2's fusion auto-fills with their linked partners.

## Run

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Data

- Uses `data/infinite_fusion_pokedex.csv` for names and sprites.
- State is saved to `data/state.json`.

## Notes

- Only unfused Pokémon from existing pairings can be selected for a fusion.
- When you fuse two of Player 1's Pokémon, the linked Player 2 Pokémon are automatically fused in the same order.


### Unfusing
- In the **Fusions** tab, each fusion has an **Unfuse** button. This deletes the fusion and frees the four Pokémon for reuse.

- Pairings now use a single **Encounter** field shared by both players.


## Docker
\`\`\`bash
# Build and run
docker compose up -d --build

# App URL
# http://<your-host>:8501
\`\`\`

- Data persists in the bind-mounted `./data` folder on the host.
- To upgrade, pull new files and run `docker compose up -d --build` again.
