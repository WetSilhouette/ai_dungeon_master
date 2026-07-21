import json
from datetime import datetime
import asyncio
from runpy import run_path

import aiosqlite
from pydantic import with_config

DB_PATH = "games.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT UNIQUE,
            player_name TEXT NOT NULL,
            setting TEXT NOT NULL,
            combat_state TEXT DEFAULT NULL,
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
            FOREIGN KEY (game_id) REFERENCES games (game_id)
            )""")
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
async def take_action_db(game_id: str, action: str, result: str, turn_number: int, stats: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("""
            INSERT INTO turns (game_id, turn_number, action, result, stats)
            VALUES (?, ?, ?, ?, ?)
            """,
            (game_id, turn_number, action, result, stats)
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




if __name__ == "__main__":
    game_id = "krENTkENAM"
    # asyncio.run(take_action_db(game_id, action="tralala", result="Trambaleila"))
    rows = asyncio.run(get_last_turn(game_id))[2]
    print(rows)
