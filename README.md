# AI Dungeon Master

A text-adventure game engine where an LLM acts as the dungeon master: it narrates scenes, offers actions, and reacts to whatever the player types. Built with FastAPI, SQLite, and a local Ollama model, with a plain HTML/JS frontend.

## Stack

- **Backend:** Python, FastAPI, SQLite (via `aiosqlite`)
- **LLM:** [Ollama](https://ollama.com), model `gemma4` (local, no API key needed)
- **Frontend:** a single static HTML page (`static/index.html`), no build step, no framework

## Prerequisites

- Python 3.13+
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- [Ollama](https://ollama.com) running locally with the `gemma4` model pulled:
  ```bash
  ollama pull gemma4
  ```

## Running it

```bash
uv sync
uv run uvicorn main:app --reload
```

Then open `http://localhost:8000` in a browser to play, or hit the API directly (see below). The SQLite file (`games.db`) and its tables (including seed locations) are created automatically on first startup.

## Project layout

| File | Responsibility |
|---|---|
| [main.py](main.py) | FastAPI routes and all game/business logic |
| [ai.py](ai.py) | Everything that talks to the LLM (prompt building, JSON parsing/repair) |
| [db.py](db.py) | All SQLite access — schema, seed data, queries |
| [static/index.html](static/index.html) | The browser game client (story log, stats, combat, save/load) |

## How a turn works

Each call to `POST /games/{id}/action` does three things in order: resolves the action deterministically wherever possible (combat damage, movement, achievement checks, price effects — all plain Python, no LLM involved), asks the LLM only for narrative continuity and next actions, then persists the result. The LLM is treated as a narrator, not a rules engine — anything that needs to be reliable (damage numbers, stat boundaries, one-time achievements) is computed in code and only *described* by the model.

Per-game state (character stats, combat, location, achievements) lives on the `games`/`turns` rows. World events are the one piece of genuinely global state — not scoped to any single game — and get injected into every game's narration automatically while active.

## API reference

### Game lifecycle
- `POST /games` — start a new game. Body: `{player_name, setting}` (`setting` is one of `dark fantasy`, `space opera`, `post-apocalyptic`, `classic dungeon`).
- `POST /games/{game_id}/action` — take a turn. Body: `{action}` (free text, or one of the 3 offered actions).
- `POST /games/{game_id}/save` — get a memorable save code (`BRAVE-1234` format). Overwrites any previous save for that game.
- `POST /games/load` — resume a game. Body: `{save_code}`.
- `POST /games/{game_id}/end` — manually end a game early. Games also auto-end on death or at turn 30.

### Progress and history
- `GET /games/{game_id}/achievements` — achievements earned so far.
- `GET /games/{game_id}/summary` — LLM-generated title + 2-3 paragraph recap (generated once, then cached) plus final stats. 400s if the game hasn't ended.
- `GET /games/{game_id}/replay` — every turn, in chronological order.

### Admin
- `POST /admin/events` — create a world event (title, description, effects, start/end dates) that's automatically injected into every game's narration while active, and can block locations or raise shop prices. No auth — matches the rest of this prototype.

## Known limitations

- **No auth anywhere**, including the admin endpoint — fine for local/hobby use, not for anything public-facing.
- **Local LLM compliance is inconsistent.** `gemma4` doesn't always include the structured `updates`/`combat` keys the prompts ask for, even when the narrative implies a change (e.g. it may narrate spending gold without emitting the corresponding delta). The game logic tolerates this gracefully (nothing crashes, changes just don't apply that turn) rather than forcing compliance.
- **`gold_collected` reflects the LLM's reported deltas**, not itemized transactions — if the model merges "sold an item, bought a meal" into one net delta, that's what gets tracked.
