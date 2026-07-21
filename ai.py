from ollama import ChatResponse, chat
import json
import ast


MODEL = "gemma4"

JSON_FORMAT = {"scene": "...", "actions": ["...", "...", "..."]}
TURN_JSON_FORMAT = {
    "result": "...",
    "actions": ["...", "...", "..."],
    "updates": {"hp": -15, "gold": 10, "inventory": {"add": ["item"], "remove": ["item"]}}
}
COMBAT_STATE_JSON = {"in_combat": "true", "enemy": {"name": "Goblin", "hp": 30, "attack": 8}}


def clean_response(raw):
    return raw.replace("```json", "").replace("```", "").strip()


async def model_response(prompt) -> dict:
    response: ChatResponse = chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.message.content
    cleaned = clean_response(raw)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            result = ast.literal_eval(cleaned)
        except (ValueError, SyntaxError) as e:
            raise ValueError(
                f"Model did not return valid JSON or a valid Python literal. Raw response was: \n{cleaned}"
            ) from e

    if not isinstance(result, dict):
        raise ValueError(f"Expected a JSON object, got {type(result).__name__}: {result!r}")

    if isinstance(result.get("actions"), list):
        result["actions"] = [normalize_action(item) for item in result["actions"]]

    return result


def normalize_action(item) -> str:
    """The model occasionally returns an action as an object instead of a plain string."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("action") or item.get("text") or item)
    return str(item)


def location_prompt_block(location: dict | None, arriving: bool = False) -> str:
    if not location:
        return ""
    block = f"""Current location: {location['name']} - {location['description']} (atmosphere: {location['atmosphere']})."""
    if arriving:
        block += (" The player has just arrived here - describe their arrival and first impressions of this"
                   " specific place, grounded in its atmosphere, not a continuation of wherever they were before.")
    return block


def world_events_prompt_block(world_events: list | None) -> str:
    if not world_events:
        return ""
    descriptions = "; ".join(f"{e['title']} - {e['description']}" for e in world_events)
    return (f"Current world events affecting the setting: {descriptions}. Let this shape the world naturally"
            f" - NPC dialogue, rumors, and the atmosphere should reflect it without needing to be told to.")


async def start_game(game_input, location: dict | None = None, world_events: list | None = None) -> dict:
    """"Come up with unique game like D&D according to input data"""

    location_block = location_prompt_block(location)
    events_block = world_events_prompt_block(world_events)
    prompt = f"""You are a dungeon master. Start a {game_input.setting}
                adventure for a player named {game_input.player_name}. {location_block}
                {events_block}
                Write a 3-5 sentence opening scene grounded in this location and, if applicable, the world events above.
                Then provide exactly 3 possible actions as a JSON array.
                Return ONLY valid JSON using double quotes for all keys and strings.
                Do not use single quotes or Python dict syntax.
                Return ONLY: {JSON_FORMAT}"""
    result = await model_response(prompt)
    return result


async def continue_game(game_history, stats, location: dict | None = None, arriving: bool = False,
                          world_events: list | None = None) -> dict:
    location_block = location_prompt_block(location, arriving=arriving)
    events_block = world_events_prompt_block(world_events)
    prompt = f"""You are a dungeon master. Continue a game with such actions history and world building {game_history}.
                Current character stats: {json.dumps(stats)}.
                {location_block}
                {events_block}
                Write a 3-5 sentence continuation scene that reflects the outcome of the player's latest action.
                Then provide exactly 3 possible actions as a JSON array.
                If the latest action changes HP, gold, or inventory in any way (taking damage, defeating an
                enemy, looting, finding or using an item, etc.), you MUST include an "updates" key with deltas
                for only the fields that changed (e.g. -15 for damage taken, 10 for gold found). Omit "updates"
                entirely only if nothing changed.
                If your scene introduces a hostile enemy that the player must now fight, include a "combat" key
                describing it: {COMBAT_STATE_JSON}. Give the enemy an hp and attack value that is a fair
                challenge for the player's own stats. Omit "combat" entirely if no new fight is starting right now.
                Return ONLY valid JSON in this exact shape, using double quotes for all keys and strings: {TURN_JSON_FORMAT}"""

    result = await model_response(prompt)
    print(result)
    return result


async def generate_summary(full_story: str) -> dict:
    prompt = f"""You are a dungeon master writing the closing recap of a finished tabletop adventure.
                Here is the full story, turn by turn:
                {full_story}
                Write a 2-3 paragraph narrative summary of this adventure, along with a short evocative title.
                Base the summary on what actually happened in the story above, not just a generic recap.
                Return ONLY valid JSON using double quotes for all keys and strings, in this exact shape:
                {{"title": "...", "summary": "..."}}"""
    result = await model_response(prompt)
    return result


async def narrate_combat(outcome_summary: str) -> str:
    """Narrate one combat round whose numbers were already decided by game logic - do not invent different ones."""
    prompt = f"""You are a dungeon master narrating one round of combat that has already been resolved by the
                game's rules. Exactly what happened: {outcome_summary}
                Write 2-3 vivid sentences narrating exactly this outcome. Do not change the damage numbers or
                the result described above. Return ONLY the narration as plain text - no JSON, no quotes."""
    response: ChatResponse = chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    return clean_response(response.message.content)


if __name__ == "__main__":
    mock_input = {
  "player_name": "Aria",
  "setting": "dark fantasy"
}
    mock_input = json.dumps(mock_input)
    # mock_turn_history =


    # print(start_game(mock_input))
    # print(continue_game())