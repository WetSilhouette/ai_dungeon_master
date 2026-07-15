from ollama import ChatResponse, chat
import json
import ast


MODEL = "gemma4"

JSON_FORMAT = {"scene": "...", "actions": ["...", "...", "..."]}
TURN_JSON_FORMAT = {"result": "...", "actions": ["...", "...", "..."]}


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
            result = json.loads(ast.literal_eval(cleaned))
        except (ValueError, SyntaxError) as e:
            raise ValueError(
                f"Model did not return valid JSON or a valid Python literal. Raw response was: \n{cleaned}"
            ) from e

    if not isinstance(result, dict):
        raise ValueError(f"Expected a JSON object, got {type(result).__name__}: {result!r}")

    return result


async def start_game(game_input) -> dict:
    """"Come up with unique game like D&D according to input data"""

    prompt = f"""You are a dungeon master. Start a {game_input.setting}
                adventure for a player named {game_input.player_name}. Write a 3-5 sentence opening scene. 
                Then provide exactly 3 possible actions as a JSON array. 
                Return ONLY valid JSON using double quotes for all keys and strings. 
                Do not use single quotes or Python dict syntax.
                Return ONLY: {JSON_FORMAT}"""
    result = await model_response(prompt)
    return result


async def continue_game(game_history) -> dict:
    prompt = f"""You are a dungeon master. Continue a game with such actions history and world building {game_history}. Write a 3-5 sentence continuation scene. 
                Then provide exactly 3 possible actions as a JSON array. 
                Return ONLY: {TURN_JSON_FORMAT}"""

    result = await model_response(prompt)
    return result


if __name__ == "__main__":
    mock_input = {
  "player_name": "Aria",
  "setting": "dark fantasy"
}
    mock_input = json.dumps(mock_input)
    # mock_turn_history =


    # print(start_game(mock_input))
    # print(continue_game())