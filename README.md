Pokémon Infinite Fusion Soullllink Tracker

A web-based application built with Streamlit to help players track their progress in a Pokémon Infinite Fusion "Soullink" Nuzlocke challenge. This tool allows two players to manage their paired Pokémon encounters, create fusions, maintain a team roster, and keep a graveyard of fainted Pokémon.
Overview

In a Soullink run, two players link their Pokémon encounters. If one player's Pokémon faints, its linked partner for the other player is also considered lost. This tracker is specifically designed for the "Infinite Fusion" fan game, where any two Pokémon can be fused together, adding another layer of complexity. This application helps manage these unique game mechanics in a user-friendly interface.
Features

    Pairing Management: Add new Pokémon pairings for Player 1 and Player 2 based on their in-game encounters.

    Fusion Creation: Fuse two Pokémon from a player's available pairings to create a powerful new creature. The app automatically links the fusions for both players.

    Team Roster: A dedicated tab to manage each player's active team of up to six Pokémon. You can add both individual and fused Pokémon to the team.

    Graveyard: Send fainted pairings or fusions to the graveyard to keep track of losses.

    Evolution Tracking: Evolve your Pokémon directly from the UI. Evolutions are reflected in pairings, fusions, and on your team.

    Search & Filter: Easily search through your pairings, fusions, and graveyard to find specific Pokémon.

    Data Persistence: Your session is automatically saved to a local state.json file, so you can close the app and pick up where you left off.

How to Use
Prerequisites

    Python 3.8+

    pip (Python package installer)

Setup and Installation

    Download the project files:

        app.py

        ui_components.py

        storage.py

    Create a project directory and place the downloaded files inside.

    Create a data sub-directory in your project folder. This is where the Pokédex and your save file will be stored.

    Add the Pokédex:

        You will need a CSV file named infinite_fusion_pokedex.csv inside the data directory.

        This file should contain information about the Pokémon, including at minimum their number, name, and a path/URL to their sprite.

    Install dependencies:
    Open a terminal or command prompt in your project directory and run:

    pip install streamlit pandas

    Run the application:
    In the same terminal, run the following command:

    streamlit run app.py

    Your web browser should open with the application running locally.

File Structure

    app.py: The main application file. It handles the Streamlit interface, tabs, state management, and overall application logic.

    ui_components.py: Contains functions that generate the visual components for the app, such as Pokémon display cards, fusion tiles, and team rosters.

    storage.py: Manages data loading and saving. It reads the Pokédex CSV and handles the state.json file where all user data is stored.

    data/: This directory holds the necessary data files.

        infinite_fusion_pokedex.csv: (User-provided) The database of all Pokémon.

        state.json: (Auto-generated) The save file for your entire session.

Dependencies

    streamlit: The core framework for building the web application.

    pandas: Used for loading and managing the Pokédex data from the CSV file.
