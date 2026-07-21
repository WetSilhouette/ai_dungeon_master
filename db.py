import json
from datetime import datetime
import asyncio
from runpy import run_path

import aiosqlite
from pydantic import with_config

DB_PATH = "games.db"

DEFAULT_LOCATIONS = [
    {"id": "tavern", "name": "The Rusty Tankard Tavern",
     "description": "A smoky, low-ceilinged tavern full of hushed conversation and the smell of stale ale.",
     "atmosphere": "warm, crowded, and gossip-filled"},
    {"id": "town_square", "name": "Town Square",
     "description": "The heart of town, ringed by market stalls and a cracked stone fountain.",
     "atmosphere": "bustling and loud by day, eerily quiet at night"},
    {"id": "dark_forest", "name": "Dark Forest",
     "description": "A dense, ancient forest where the canopy blots out most of the daylight.",
     "atmosphere": "cold, damp, and watchful"},
    {"id": "ancient_ruins", "name": "Ancient Ruins",
     "description": "Crumbling stone structures overtaken by moss, remnants of a civilization long gone.",
     "atmosphere": "silent, reverent, and unsettling"},
    {"id": "deep_dungeon", "name": "Deep Dungeon",
     "description": "A labyrinth of torch-lit corridors carved deep beneath the earth.",
     "atmosphere": "oppressive, dank, and dangerous"},
]

DEFAULT_EXITS = [
    ("tavern", "town_square"), ("town_square", "tavern"),
    ("town_square", "dark_forest"), ("dark_forest", "town_square"),
    ("town_square", "ancient_ruins"), ("ancient_ruins", "town_square"),
    ("dark_forest", "deep_dungeon"), ("deep_dungeon", "dark_forest"),
]


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT UNIQUE,
            player_name TEXT NOT NULL,
            setting TEXT NOT NULL,
            combat_state TEXT DEFAULT NULL,
            location_state TEXT DEFAULT NULL,
            combat_wins INTEGER DEFAULT 0,
            gold_collected INTEGER DEFAULT 0,
            ended INTEGER DEFAULT 0,
            summary_title TEXT DEFAULT NULL,
            summary_text TEXT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP)
        """)
        await db.commit()
        await db.execute("""CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            turn_number INT NOT NULL,
            action TEXT NOT NULL,
            result TEXT NOT NULL,
            stats TEXT DEFAULT '{...}',
            actions TEXT DEFAULT '[]',
            FOREIGN KEY (game_id) REFERENCES games (game_id)
            )""")
        await db.commit()
        await db.execute("""CREATE TABLE IF NOT EXISTS saves (
            save_code TEXT PRIMARY KEY,
            game_id TEXT NOT NULL,
            saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games (game_id)
            )""")
        await db.commit()
        await db.execute("""CREATE TABLE IF NOT EXISTS locations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            atmosphere TEXT NOT NULL
            )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS location_exits (
            from_location TEXT NOT NULL,
            to_location TEXT NOT NULL,
            PRIMARY KEY (from_location, to_location),
            FOREIGN KEY (from_location) REFERENCES locations (id),
            FOREIGN KEY (to_location) REFERENCES locations (id)
            )""")
        await db.commit()
        await db.execute("""CREATE TABLE IF NOT EXISTS achievements (
            game_id TEXT NOT NULL,
            achievement_id TEXT NOT NULL,
            earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (game_id, achievement_id),
            FOREIGN KEY (game_id) REFERENCES games (game_id)
            )""")
        await db.commit()

        for location in DEFAULT_LOCATIONS:
            await db.execute(
                "INSERT OR IGNORE INTO locations (id, name, description, atmosphere) VALUES (?, ?, ?, ?)",
                (location["id"], location["name"], location["description"], location["atmosphere"])
            )
        for from_id, to_id in DEFAULT_EXITS:
            await db.execute(
                "INSERT OR IGNORE INTO location_exits (from_location, to_location) VALUES (?, ?)",
                (from_id, to_id)
            )
        await db.commit()


# Save the newly created game in /games
async def save_game(game_id: str, game_inputs) -> int:
    player_name = game_inputs.player_name
    setting = game_inputs.setting
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO games (game_id, player_name, setting, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (game_id, player_name, setting, created_at)
        )
        await db.commit()
        return cursor.lastrowid


# Get last row from character's turns for this game_id
async def get_last_turn(game_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT * 
            FROM turns 
            WHERE game_id = ? 
            ORDER BY turn_number DESC 
            LIMIT 1
        """, (game_id,))
        return await cursor.fetchone()


# Get all rows from character's turns for this game_id
async def get_game_history(game_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT * 
            FROM turns 
            WHERE game_id = ? 
            ORDER BY turn_number DESC 
        """, (game_id,))
        return await cursor.fetchall()


# Add character's turn to the 'turns' table
async def take_action_db(game_id: str, action: str, result: str, turn_number: int, stats: str, actions: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("""
            INSERT INTO turns (game_id, turn_number, action, result, stats, actions)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (game_id, turn_number, action, result, stats, actions)
            )
        await db.commit()
        return cursor.lastrowid


# Update turn action to character's choice
async def update_action(game_id: str, action: str, turn_number: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE turns
            SET action = ?
            WHERE game_id = ? AND turn_number = ?
            """,
            (action, game_id, turn_number)
            )
        await db.commit()
        return cursor.lastrowid


# Update combat state in games table
async def update_combat_state(game_id: str, combat_state_json: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE games
            SET combat_state = ?
            WHERE game_id = ?
            """,
            (combat_state_json, game_id)
            )
        await db.commit()
        return cursor.lastrowid


# Get combat state
async def get_combat_state(game_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT combat_state
            FROM games
            WHERE game_id = ?
        """, (game_id,))
        await db.commit()
        return await cursor.fetchone()


# Check whether a game exists
async def get_game(game_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT game_id, player_name, setting
            FROM games
            WHERE game_id = ?
        """, (game_id,))
        return await cursor.fetchone()


# Create a save code for a game, replacing any existing save for that game
async def create_save(game_id: str, save_code: str, saved_at: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM saves WHERE game_id = ?", (game_id,))
        await db.execute("""
            INSERT INTO saves (save_code, game_id, saved_at)
            VALUES (?, ?, ?)
            """,
            (save_code, game_id, saved_at)
            )
        await db.commit()


# Look up the game_id for a save code
async def get_save(save_code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT game_id
            FROM saves
            WHERE save_code = ?
        """, (save_code,))
        return await cursor.fetchone()


# Get one location's details
async def get_location(location_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, name, description, atmosphere
            FROM locations
            WHERE id = ?
        """, (location_id,))
        return await cursor.fetchone()


# Get the locations reachable from a given location, as (id, name) pairs
async def get_location_exits(location_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT l.id, l.name
            FROM location_exits e
            JOIN locations l ON l.id = e.to_location
            WHERE e.from_location = ?
        """, (location_id,))
        return await cursor.fetchall()


# Get a game's location state
async def get_location_state(game_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT location_state
            FROM games
            WHERE game_id = ?
        """, (game_id,))
        return await cursor.fetchone()


# Update a game's location state
async def update_location_state(game_id: str, location_state_json: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE games
            SET location_state = ?
            WHERE game_id = ?
            """,
            (location_state_json, game_id)
            )
        await db.commit()
        return cursor.lastrowid


# Increment a game's total combat victories
async def increment_combat_wins(game_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE games
            SET combat_wins = combat_wins + 1
            WHERE game_id = ?
            """,
            (game_id,)
            )
        await db.commit()
        return cursor.lastrowid


# Get a game's total combat victories
async def get_combat_wins(game_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT combat_wins FROM games WHERE game_id = ?", (game_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


# Get the achievement ids already earned for a game
async def get_earned_achievements(game_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT achievement_id FROM achievements WHERE game_id = ?", (game_id,))
        return await cursor.fetchall()


# Award an achievement, ignoring if it was already earned
async def award_achievement(game_id: str, achievement_id: str, earned_at: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO achievements (game_id, achievement_id, earned_at) VALUES (?, ?, ?)",
            (game_id, achievement_id, earned_at)
        )
        await db.commit()


# Mark a game as manually ended
async def mark_game_ended(game_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE games SET ended = 1 WHERE game_id = ?", (game_id,))
        await db.commit()


# Check whether a game was manually ended
async def is_game_ended(game_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT ended FROM games WHERE game_id = ?", (game_id,))
        row = await cursor.fetchone()
        return bool(row and row[0])


# Add to a game's lifetime gold-collected counter
async def increment_gold_collected(game_id: str, amount: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE games SET gold_collected = gold_collected + ? WHERE game_id = ?",
            (amount, game_id)
        )
        await db.commit()


# Get a game's lifetime gold-collected total
async def get_gold_collected(game_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT gold_collected FROM games WHERE game_id = ?", (game_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


# Get a game's cached summary, if generated
async def get_summary(game_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT summary_title, summary_text FROM games WHERE game_id = ?", (game_id,))
        return await cursor.fetchone()


# Cache a generated summary
async def save_summary(game_id: str, title: str, summary_text: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE games SET summary_title = ?, summary_text = ? WHERE game_id = ?",
            (title, summary_text, game_id)
        )
        await db.commit()




if __name__ == "__main__":
    game_id = "krENTkENAM"
    # asyncio.run(take_action_db(game_id, action="tralala", result="Trambaleila"))
    rows = asyncio.run(get_last_turn(game_id))[2]
    print(rows)
