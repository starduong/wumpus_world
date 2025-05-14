import asyncio
import platform
import pygame
import os
import re
import subprocess
import shutil

# --- Configuration ---
PROLOG_EXECUTABLE = "swipl"
PROLOG_SCRIPT = "wumpus_agent.pl"
KB_FILE_PATH = "kb.txt"

# --- Pygame Setup ---
pygame.init()
pygame.font.init()

# Screen dimensions
SCREEN_WIDTH = 950
SCREEN_HEIGHT = 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Wumpus World (Simulated from kb.txt)")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GOLD_COLOR = (255, 215, 0)
LIGHT_BLUE = (173, 216, 230)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
DIM_COLOR = (0, 0, 0, 150)  # Semi-transparent black for dimming

# Fonts
FONT_SMALL = pygame.font.SysFont("arial", 18)
FONT_MEDIUM = pygame.font.SysFont("arial", 22)
FONT_LARGE = pygame.font.SysFont("arial", 28)

# Grid settings
CELL_SIZE = 70
GRID_MARGIN_X = 50
GRID_MARGIN_Y = 50
WORLD_DIM = 4

# --- Asset Loading ---
agent_img = None
wumpus_img = None
pit_img = None
gold_img = None
stench_img = None
breeze_img = None
glitter_img = None
start_node_img = None
arrow_img = None
safe_img = None
question_mark_img = None


def load_image(name, size=(CELL_SIZE - 10, CELL_SIZE - 10)):
    try:
        path = os.path.join("images", name)
        if not os.path.exists(path):
            path = name
            if not os.path.exists(path):
                path_no_ext = os.path.splitext(name)[0]
                if os.path.exists(path_no_ext):
                    path = path_no_ext
                else:
                    print(f"Cannot find image file: {name}")
                    surface = pygame.Surface(size)
                    surface.fill(GRAY)
                    text = FONT_SMALL.render(name.split(".")[0][:3], True, BLACK)
                    text_rect = text.get_rect(center=(size[0] // 2, size[1] // 2))
                    surface.blit(text, text_rect)
                    return surface

        image = pygame.image.load(path)
        image = pygame.transform.scale(image, size)
        return image
    except pygame.error as e:
        print(f"Cannot load image: {name} - {e}")
        surface = pygame.Surface(size)
        surface.fill(GRAY)
        text = FONT_SMALL.render(name.split(".")[0][:3], True, BLACK)
        text_rect = text.get_rect(center=(size[0] // 2, size[1] // 2))
        surface.blit(text, text_rect)
        return surface
    except FileNotFoundError:
        print(f"Cannot find image file: {name}")
        surface = pygame.Surface(size)
        surface.fill(GRAY)
        text = FONT_SMALL.render(name.split(".")[0][:3], True, BLACK)
        text_rect = text.get_rect(center=(size[0] // 2, size[1] // 2))
        surface.blit(text, text_rect)
        return surface


def create_question_mark_img(size):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    text = FONT_MEDIUM.render("?", True, RED)
    text_rect = text.get_rect(center=(size[0] // 2, size[1] // 2))
    surface.blit(text, text_rect)
    return surface


def load_all_images():
    global agent_img, wumpus_img, pit_img, gold_img, stench_img, breeze_img, glitter_img
    global start_node_img, arrow_img, safe_img, question_mark_img
    entity_size = (int(CELL_SIZE * 0.8), int(CELL_SIZE * 0.8))
    percept_icon_size = (int(CELL_SIZE * 0.4), int(CELL_SIZE * 0.4))
    safe_icon_size = (int(CELL_SIZE * 0.5), int(CELL_SIZE * 0.5))

    agent_img = load_image("../image/agent.png", entity_size)
    wumpus_img = load_image("../image/wumpus.png", entity_size)
    pit_img = load_image("../image/pit.png", entity_size)
    gold_img = load_image("../image/gold.png", entity_size)
    stench_img = load_image("../image/stench.png", percept_icon_size)
    breeze_img = load_image("../image/breeze.png", percept_icon_size)
    glitter_img = load_image("../image/glitter.png", percept_icon_size)
    arrow_img = load_image("../image/arrow.png", (CELL_SIZE // 2, CELL_SIZE // 4))
    safe_img = load_image("../image/safe.png", safe_icon_size)
    question_mark_img = create_question_mark_img(entity_size)

    surf = pygame.Surface(entity_size, pygame.SRCALPHA)
    pygame.draw.circle(
        surf, GREEN, (entity_size[0] // 2, entity_size[1] // 2), entity_size[0] // 3
    )
    start_text_render = FONT_SMALL.render("S", True, BLACK)
    start_text_rect = start_text_render.get_rect(
        center=(entity_size[0] // 2, entity_size[1] // 2)
    )
    surf.blit(start_text_render, start_text_rect)
    start_node_img = surf


load_all_images()

# --- Game State Variables ---
initial_agent_pos_prolog = [1, 1]
pit_locations_prolog = [[4, 4], [3, 3], [3, 1]]
wumpus_location_prolog = [1, 3]
gold_location_prolog = [3, 2]
simulation_steps_data = []
current_step_index = -1
simulation_agent_pos = list(initial_agent_pos_prolog)
simulation_agent_path = [list(initial_agent_pos_prolog)]
simulation_score = 0
simulation_time_taken = 0
simulation_game_status = "init"
simulation_percepts_current = None
simulation_wumpus_status = "alive"
simulation_wumpus_location = list(wumpus_location_prolog)
safe_locations = []
maybe_wumpus_locations = []
no_wumpus_locations = []
maybe_pit_locations = []
no_pit_locations = []
visited_locations = [list(initial_agent_pos_prolog)]
step_by_step_mode = True
simulation_running = False
message_log = [
    "Welcome to Wumpus World (Simulated)! Please click 'Start Sim' to begin."
]
MAX_LOG_LINES = 15
last_auto_step_time = 0


# --- Helper Functions ---
def prolog_to_grid_coords(prolog_x, prolog_y):
    grid_col = prolog_x - 1
    grid_row = WORLD_DIM - prolog_y
    return grid_col, grid_row


def grid_to_screen_coords(grid_col, grid_row):
    screen_x = (
        GRID_MARGIN_X + grid_col * CELL_SIZE + (CELL_SIZE - agent_img.get_width()) // 2
    )
    screen_y = (
        GRID_MARGIN_Y + grid_row * CELL_SIZE + (CELL_SIZE - agent_img.get_height()) // 2
    )
    return screen_x, screen_y


def add_message(msg):
    print(f"UI_LOG: {msg}")
    message_log.insert(0, msg)
    if len(message_log) > MAX_LOG_LINES:
        message_log.pop()


def parse_prolog_coord(coord_str):
    match = re.search(r"\[(\d+),(\d+)\]", coord_str)
    if match:
        return [int(match.group(1)), int(match.group(2))]
    return None


def parse_prolog_percepts(percept_str):
    match = re.search(r"\[(yes|no),(yes|no),(yes|no)\]", percept_str)
    if match:
        return [match.group(1), match.group(2), match.group(3)]
    match_vars = re.search(r"\[(_\d+),(_\d+),(_\d+)\]", percept_str)
    if match_vars:
        return ["no", "no", "no"]
    print(f"Warning: Could not parse percepts: {percept_str}")
    return ["?", "?", "?"]


# --- Prolog Execution ---
def find_prolog_executable(name=PROLOG_EXECUTABLE):
    path = shutil.which(name)
    if path:
        add_message(f"Found Prolog executable: {path}")
        return path
    else:
        add_message(
            f"Warning: '{name}' not found in PATH. Assuming it's callable directly."
        )
        return name


def run_prolog_script():
    global simulation_game_status
    prolog_cmd = find_prolog_executable()
    if not prolog_cmd:
        add_message(
            f"ERROR: Cannot find Prolog executable ('{PROLOG_EXECUTABLE}'). Please install SWI-Prolog."
        )
        simulation_game_status = "error"
        return False

    if not os.path.exists(PROLOG_SCRIPT):
        add_message(f"ERROR: Prolog script '{PROLOG_SCRIPT}' not found.")
        simulation_game_status = "error"
        return False

    command = [prolog_cmd, "-s", PROLOG_SCRIPT, "-g", "start.", "-t", "halt."]
    add_message(f"Running Prolog: {' '.join(command)}")
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=15, check=False
        )
        if result.returncode != 0:
            add_message(
                f"ERROR: Prolog script exited with error code {result.returncode}."
            )
            add_message("--- Prolog stdout: ---")
            add_message(result.stdout if result.stdout else "<empty>")
            add_message("--- Prolog stderr: ---")
            add_message(result.stderr if result.stderr else "<empty>")
            simulation_game_status = "error"
            if os.path.exists(KB_FILE_PATH):
                try:
                    os.remove(KB_FILE_PATH)
                    add_message(f"Removed potentially incomplete {KB_FILE_PATH}.")
                except OSError as e:
                    add_message(f"Warning: Could not remove {KB_FILE_PATH}: {e}")
            return False
        else:
            add_message("Prolog script executed successfully.")
            if not os.path.exists(KB_FILE_PATH):
                add_message(
                    f"ERROR: Prolog script finished, but '{KB_FILE_PATH}' was not created."
                )
                add_message("--- Prolog stdout: ---")
                add_message(result.stdout if result.stdout else "<empty>")
                add_message("--- Prolog stderr: ---")
                add_message(result.stderr if result.stderr else "<empty>")
                simulation_game_status = "error"
                return False
            return True
    except FileNotFoundError:
        add_message(
            f"ERROR: Prolog command '{prolog_cmd}' not found. Is SWI-Prolog installed?"
        )
        simulation_game_status = "error"
        return False
    except subprocess.TimeoutExpired:
        add_message("ERROR: Prolog script timed out (took longer than 15 seconds).")
        simulation_game_status = "error"
        return False
    except Exception as e:
        add_message(f"ERROR: An unexpected error occurred while running Prolog: {e}")
        simulation_game_status = "error"
        return False


# --- KB.TXT Parsing Logic ---
def load_and_parse_kb_log(filepath=KB_FILE_PATH):
    global simulation_steps_data, simulation_wumpus_location, simulation_wumpus_status
    simulation_steps_data = []
    if not os.path.exists(filepath):
        add_message(f"ERROR: Cannot find simulation file {filepath}")
        return False
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except Exception as e:
        add_message(f"ERROR: Could not read file {filepath}: {e}")
        return False

    rounds_text = content.split("New Round:")[1:]
    if not rounds_text:
        add_message(f"ERROR: No 'New Round:' sections found in {filepath}")
        if not content.strip():
            add_message("File is empty.")
        else:
            add_message("File content does not contain expected 'New Round:' markers.")
        return False

    current_round_num = 0
    current_wumpus_status = "alive"
    current_wumpus_location = simulation_wumpus_location
    safe_locations.clear()
    maybe_wumpus_locations.clear()
    no_wumpus_locations.clear()
    maybe_pit_locations.clear()
    no_pit_locations.clear()
    visited_locations.clear()
    visited_locations.append(list(initial_agent_pos_prolog))

    for round_block in rounds_text:
        step_info = {
            "round": current_round_num,
            "start_location": None,
            "percepts": None,
            "action": None,
            "next_location": None,
            "score": None,
            "time": None,
            "end_status": "playing",
            "wumpus_status": current_wumpus_status,
            "wumpus_location": current_wumpus_location,
            "safe_locations": list(safe_locations),
            "maybe_wumpus_locations": list(maybe_wumpus_locations),
            "no_wumpus_locations": list(no_wumpus_locations),
            "maybe_pit_locations": list(maybe_pit_locations),
            "no_pit_locations": list(no_pit_locations),
            "visited_locations": list(visited_locations),
            "messages": [],
            "raw_text": round_block,
        }

        lines = round_block.strip().split("\n")
        agent_at_start = None
        percepts_at_start = None
        action_info = None
        new_time = None
        new_score = None
        end_status_in_round = "playing"

        for line in lines:
            line = line.strip()
            if line.startswith("I am at"):
                match = re.search(r"I am at (\[\d+,\d+\])", line)
                if match:
                    agent_at_start = parse_prolog_coord(match.group(1))
                    step_info["start_location"] = agent_at_start
                    if agent_at_start not in visited_locations:
                        visited_locations.append(agent_at_start)

            elif "seeing:" in line:
                match = re.search(r"seeing: (\[.*?\])", line)
                if match:
                    percepts_at_start = parse_prolog_percepts(match.group(1))
                    step_info["percepts"] = percepts_at_start

            elif line.startswith("I'm going to:"):
                match = re.search(r"I\'m going to: (\[\d+,\d+\])", line)
                if match:
                    action_target = parse_prolog_coord(match.group(1))
                    action_info = {"type": "move", "target": action_target}
                    step_info["next_location"] = action_target
                    step_info["messages"].append(line)

            elif line.startswith("I shoot an arrow at"):
                match = re.search(r"I shoot an arrow at (\[\d+,\d+\])!", line)
                if match:
                    shoot_target = parse_prolog_coord(match.group(1))
                    action_info = {"type": "shoot", "target": shoot_target}
                    step_info["action"] = action_info
                    step_info["messages"].append(line)

            elif line.startswith("I grab the gold!"):
                action_info = {"type": "grab"}
                step_info["action"] = action_info
                step_info["messages"].append(line)

            elif line.startswith("Wumpus at"):
                match = re.search(r"Wumpus at (\[\d+,\d+\]) is killed!", line)
                if match:
                    current_wumpus_status = "dead"
                    killed_location = parse_prolog_coord(match.group(1))
                    action_info["result"] = (
                        "killed"
                        if action_info and action_info["type"] == "shoot"
                        else None
                    )
                    step_info["wumpus_status"] = current_wumpus_status
                    maybe_wumpus_locations.clear()
                    step_info["messages"].append(line)

            elif line.startswith("KB learn") and (
                "is now OK" in line or "is OK" in line
            ):
                match = re.search(r"KB learn (\[\d+,\d+\]) (?:is now OK|is OK)", line)
                if match:
                    safe_loc = parse_prolog_coord(match.group(1))
                    if safe_loc not in safe_locations:
                        safe_locations.append(safe_loc)
                    step_info["safe_locations"] = list(safe_locations)
                    step_info["messages"].append(f"KB learn {match.group(1)} is OK")

            elif line.startswith("KB learn") and "maybe there is a Wumpus" in line:
                match = re.search(
                    r"KB learn (\[\d+,\d+\]) - maybe there is a Wumpus!", line
                )
                if match:
                    wumpus_loc = parse_prolog_coord(match.group(1))
                    if (
                        wumpus_loc not in maybe_wumpus_locations
                        and wumpus_loc not in no_wumpus_locations
                    ):
                        maybe_wumpus_locations.append(wumpus_loc)
                    step_info["maybe_wumpus_locations"] = list(maybe_wumpus_locations)
                    step_info["messages"].append(line)

            elif line.startswith("KB learn") and "no Wumpus there" in line:
                match = re.search(r"KB learn (\[\d+,\d+\]) - no Wumpus there!", line)
                if match:
                    no_wumpus_loc = parse_prolog_coord(match.group(1))
                    if no_wumpus_loc not in no_wumpus_locations:
                        no_wumpus_locations.append(no_wumpus_loc)
                        if no_wumpus_loc in maybe_wumpus_locations:
                            maybe_wumpus_locations.remove(no_wumpus_loc)
                    step_info["no_wumpus_locations"] = list(no_wumpus_locations)
                    step_info["maybe_wumpus_locations"] = list(maybe_wumpus_locations)
                    step_info["messages"].append(line)

            elif line.startswith("KB learn") and "is definitely at" in line:
                match = re.search(
                    r"KB learn Wumpus is definitely at (\[\d+,\d+\])", line
                )
                if match:
                    confirmed_wumpus = parse_prolog_coord(match.group(1))
                    maybe_wumpus_locations.clear()
                    maybe_wumpus_locations.append(confirmed_wumpus)
                    step_info["wumpus_location"] = confirmed_wumpus
                    current_wumpus_location = confirmed_wumpus
                    step_info["maybe_wumpus_locations"] = list(maybe_wumpus_locations)
                    step_info["messages"].append(
                        f"KB learn Wumpus is definitely at {match.group(1)}"
                    )

            elif line.startswith("KB learn") and "maybe there is a Pit" in line:
                match = re.search(
                    r"KB learn (\[\d+,\d+\]) - maybe there is a Pit!", line
                )
                if match:
                    pit_loc = parse_prolog_coord(match.group(1))
                    if (
                        pit_loc not in maybe_pit_locations
                        and pit_loc not in no_pit_locations
                    ):
                        maybe_pit_locations.append(pit_loc)
                    step_info["maybe_pit_locations"] = list(maybe_pit_locations)
                    step_info["messages"].append(line)

            elif line.startswith("KB learn") and "no Pit there" in line:
                match = re.search(
                    r"KB learn (\[\d+,\d+\]) - there is no Pit there!", line
                )
                if match:
                    no_pit_loc = parse_prolog_coord(match.group(1))
                    if no_pit_loc not in no_pit_locations:
                        no_pit_locations.append(no_pit_loc)
                        if no_pit_loc in maybe_pit_locations:
                            maybe_pit_locations.remove(no_pit_loc)
                    step_info["no_pit_locations"] = list(no_pit_locations)
                    step_info["maybe_pit_locations"] = list(maybe_pit_locations)
                    step_info["messages"].append(line)

            elif line.startswith("KB learn") and "glitter detected" in line:
                match = re.search(r"KB learn (\[\d+,\d+\]) - glitter detected!", line)
                if match:
                    step_info["messages"].append(line)

            elif line.startswith("KB learn") and "GOT THE GOLD" in line:
                match = re.search(r"KB learn (\[\d+,\d+\]) - GOT THE GOLD!!!", line)
                if match:
                    step_info["messages"].append(line)
                    end_status_in_round = "won"

            elif line == "WON!":
                end_status_in_round = "won"
                step_info["messages"].append("WON!")
            elif "AGENT GRABBED THE GOLD!!" in line:
                end_status_in_round = "won"
                step_info["messages"].append("AGENT GRABBED THE GOLD!!")
            elif "Lost: Wumpus eats you!" in line or "eaten by the wumpus!" in line:
                end_status_in_round = "lost_wumpus"
            elif "Lost: you fell into the pit!" in line or "fallen into a pit!" in line:
                end_status_in_round = "lost_pit"

            elif line.startswith("New time:"):
                match = re.search(r"New time: (\d+)", line)
                if match:
                    new_time = int(match.group(1))
                    step_info["time"] = new_time

            elif line.startswith("New score:"):
                match = re.search(r"New score: (-?\d+)", line)
                if match:
                    new_score = int(match.group(1))
                    step_info["score"] = new_score

        step_info["end_status"] = end_status_in_round
        step_info["action"] = action_info
        step_info["visited_locations"] = list(visited_locations)

        if (
            step_info["start_location"]
            and step_info["percepts"]
            and (step_info["next_location"] or step_info["action"])
            and step_info["time"] is not None
            and step_info["score"] is not None
        ):
            simulation_steps_data.append(step_info)
            current_round_num += 1
        else:
            add_message(
                f"Warning: Incomplete data for round {current_round_num+1}. Skipping."
            )
            print(f"Debug: Incomplete step data: {step_info}")

    if not simulation_steps_data:
        add_message(f"ERROR: Could not parse any valid steps from {filepath}")
        return False

    add_message(
        f"Successfully parsed {len(simulation_steps_data)} steps from {filepath}"
    )
    return True


# --- Drawing Functions ---
def draw_grid():
    for r_idx_pygame in range(WORLD_DIM):
        for c_idx_pygame in range(WORLD_DIM):
            rect = pygame.Rect(
                GRID_MARGIN_X + c_idx_pygame * CELL_SIZE,
                GRID_MARGIN_Y + r_idx_pygame * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE,
            )
            pygame.draw.rect(screen, BLACK, rect, 1)
            prolog_x = c_idx_pygame + 1
            prolog_y = WORLD_DIM - r_idx_pygame
            coord_text = FONT_SMALL.render(f"({prolog_x},{prolog_y})", True, GRAY)
            screen.blit(coord_text, (rect.x + 5, rect.y + 5))
            # Dim unvisited and unknown cells
            cell = [prolog_x, prolog_y]
            if current_step_index >= 0:
                visited = simulation_steps_data[current_step_index]["visited_locations"]
                safe = simulation_steps_data[current_step_index]["safe_locations"]
                maybe_wumpus = simulation_steps_data[current_step_index][
                    "maybe_wumpus_locations"
                ]
                maybe_pit = simulation_steps_data[current_step_index][
                    "maybe_pit_locations"
                ]
                known_elements = safe + maybe_wumpus + maybe_pit
                if cell not in visited and cell not in known_elements:
                    dim_surface = pygame.Surface(
                        (CELL_SIZE, CELL_SIZE), pygame.SRCALPHA
                    )
                    dim_surface.fill(DIM_COLOR)
                    screen.blit(dim_surface, (rect.x, rect.y))


def draw_world_elements():
    if current_step_index < 0:
        # Draw start position only in initial state
        if initial_agent_pos_prolog:
            col, row = prolog_to_grid_coords(
                initial_agent_pos_prolog[0], initial_agent_pos_prolog[1]
            )
            s_x, s_y = grid_to_screen_coords(col, row)
            screen.blit(start_node_img, (s_x, s_y))
        return

    step_data = simulation_steps_data[current_step_index]
    wumpus_status = step_data["wumpus_status"]
    wumpus_location = step_data["wumpus_location"]
    safe_locs = step_data["safe_locations"]
    maybe_wumpus_locs = step_data["maybe_wumpus_locations"]
    maybe_pit_locs = step_data["maybe_pit_locations"]
    percepts = step_data["percepts"]

    # Draw safe locations
    for safe_x, safe_y in safe_locs:
        col, row = prolog_to_grid_coords(safe_x, safe_y)
        s_x = GRID_MARGIN_X + col * CELL_SIZE + (CELL_SIZE - safe_img.get_width()) // 2
        s_y = GRID_MARGIN_Y + row * CELL_SIZE + (CELL_SIZE - safe_img.get_height()) // 2
        screen.blit(safe_img, (s_x, s_y))

    # Draw maybe pits (inferred from breeze percepts or KB)
    for pit_x, pit_y in maybe_pit_locs:
        col, row = prolog_to_grid_coords(pit_x, pit_y)
        s_x, s_y = grid_to_screen_coords(col, row)
        # Draw pit with 50% transparency
        pit_img_alpha = pit_img.copy()
        pit_img_alpha.set_alpha(128)
        screen.blit(pit_img_alpha, (s_x, s_y))
        # Add question mark
        q_x = s_x + (pit_img.get_width() - question_mark_img.get_width()) // 2
        q_y = s_y + (pit_img.get_height() - question_mark_img.get_height()) // 2
        screen.blit(question_mark_img, (q_x, q_y))

    # Draw gold if glitter is perceived and not grabbed
    if gold_location_prolog and step_data["end_status"] != "won":
        g_x, g_y = gold_location_prolog
        if (
            percepts
            and percepts[2] == "yes"
            and step_data["start_location"] == gold_location_prolog
        ):
            col, row = prolog_to_grid_coords(g_x, g_y)
            s_x, s_y = grid_to_screen_coords(col, row)
            screen.blit(gold_img, (s_x, s_y))

    # Draw maybe Wumpus
    for w_x, w_y in maybe_wumpus_locs:
        if [w_x, w_y] != wumpus_location or wumpus_status != "alive":
            col, row = prolog_to_grid_coords(w_x, w_y)
            s_x, s_y = grid_to_screen_coords(col, row)
            # Draw Wumpus with 50% transparency
            wumpus_img_alpha = wumpus_img.copy()
            wumpus_img_alpha.set_alpha(128)
            screen.blit(wumpus_img_alpha, (s_x, s_y))
            # Add question mark
            q_x = s_x + (wumpus_img.get_width() - question_mark_img.get_width()) // 2
            q_y = s_y + (wumpus_img.get_height() - question_mark_img.get_height()) // 2
            screen.blit(question_mark_img, (q_x, q_y))

    # Draw confirmed Wumpus
    if wumpus_status == "alive" and wumpus_location:
        w_x, w_y = wumpus_location
        if len(maybe_wumpus_locs) == 1 and [w_x, w_y] in maybe_wumpus_locs:
            col, row = prolog_to_grid_coords(w_x, w_y)
            s_x, s_y = grid_to_screen_coords(col, row)
            screen.blit(wumpus_img, (s_x, s_y))

    # Draw start position
    if initial_agent_pos_prolog:
        col, row = prolog_to_grid_coords(
            initial_agent_pos_prolog[0], initial_agent_pos_prolog[1]
        )
        s_x, s_y = grid_to_screen_coords(col, row)
        if simulation_agent_pos != initial_agent_pos_prolog:
            screen.blit(start_node_img, (s_x, s_y))


def draw_agent_path():
    if len(simulation_agent_path) > 1:
        points_screen = []
        for p_pos_prolog in simulation_agent_path:
            if isinstance(p_pos_prolog, (list, tuple)) and len(p_pos_prolog) == 2:
                col, row = prolog_to_grid_coords(p_pos_prolog[0], p_pos_prolog[1])
                center_x = GRID_MARGIN_X + col * CELL_SIZE + CELL_SIZE // 2
                center_y = GRID_MARGIN_Y + row * CELL_SIZE + CELL_SIZE // 2
                points_screen.append((center_x, center_y))
            else:
                print(f"Warning: Invalid point in agent path: {p_pos_prolog}")
        if len(points_screen) > 1:
            pygame.draw.lines(screen, BLUE, False, points_screen, 3)


def draw_action_effects():
    if current_step_index < 0:
        return
    current_step = simulation_steps_data[current_step_index]
    action = current_step.get("action")
    if action and action["type"] == "shoot":
        start_pos = current_step["start_location"]
        target_pos = action["target"]
        start_col, start_row = prolog_to_grid_coords(start_pos[0], start_pos[1])
        target_col, target_row = prolog_to_grid_coords(target_pos[0], target_pos[1])
        start_x = GRID_MARGIN_X + start_col * CELL_SIZE + CELL_SIZE // 2
        start_y = GRID_MARGIN_Y + start_row * CELL_SIZE + CELL_SIZE // 2
        target_x = GRID_MARGIN_X + target_col * CELL_SIZE + CELL_SIZE // 2
        target_y = GRID_MARGIN_Y + target_row * CELL_SIZE + CELL_SIZE // 2
        screen.blit(
            arrow_img,
            (
                start_x - arrow_img.get_width() // 2,
                start_y - arrow_img.get_height() // 2,
            ),
        )
        pygame.draw.line(screen, RED, (start_x, start_y), (target_x, target_y), 2)


def draw_agent():
    if simulation_agent_pos:
        col, row = prolog_to_grid_coords(
            simulation_agent_pos[0], simulation_agent_pos[1]
        )
        s_x, s_y = grid_to_screen_coords(col, row)
        screen.blit(agent_img, (s_x, s_y))


def draw_percepts_at_agent_location():
    if (
        simulation_percepts_current
        and simulation_agent_pos
        and simulation_game_status not in ["init", "error"]
    ):
        stench_val, breeze_val, glitter_val = simulation_percepts_current
        if stench_val == "?" and breeze_val == "?":
            return

        # Convert agent's Prolog coordinates to grid coordinates
        col_agent, row_agent = prolog_to_grid_coords(
            simulation_agent_pos[0], simulation_agent_pos[1]
        )
        icon_start_x = GRID_MARGIN_X + col_agent * CELL_SIZE + 5
        icon_y_offset = (
            GRID_MARGIN_Y
            + row_agent * CELL_SIZE
            + CELL_SIZE
            - stench_img.get_height()
            - 5
        )
        current_x = icon_start_x
        if stench_val == "yes":
            screen.blit(stench_img, (current_x, icon_y_offset))
            current_x += stench_img.get_width() + 2
        if breeze_val == "yes":
            screen.blit(breeze_img, (current_x, icon_y_offset))
            current_x += breeze_img.get_width() + 2
        if glitter_val == "yes":
            screen.blit(glitter_img, (current_x, icon_y_offset))


# --- UI Drawing ---
def draw_ui_elements():
    ui_start_x = GRID_MARGIN_X + WORLD_DIM * CELL_SIZE + 30
    button_width = 180
    button_height = 40
    y_spacing = 10

    reset_button_rect = pygame.Rect(
        ui_start_x, GRID_MARGIN_Y, button_width, button_height
    )
    start_button_rect = pygame.Rect(
        ui_start_x, reset_button_rect.bottom + y_spacing, button_width, button_height
    )
    step_button_rect = pygame.Rect(
        ui_start_x, start_button_rect.bottom + y_spacing, button_width, button_height
    )
    step_mode_button_rect = pygame.Rect(
        ui_start_x, step_button_rect.bottom + y_spacing, button_width, button_height
    )

    pygame.draw.rect(screen, RED, reset_button_rect)
    reset_text = FONT_MEDIUM.render("Reset Sim", True, WHITE)
    screen.blit(reset_text, (reset_button_rect.x + 10, reset_button_rect.y + 5))

    start_stop_text = "Start Sim"
    start_stop_color = GREEN
    start_text_color = BLACK

    if simulation_game_status == "init" or simulation_game_status == "ready":
        start_stop_text = "Start Sim"
        start_stop_color = GREEN
    elif simulation_game_status == "playing":
        if step_by_step_mode:
            start_stop_text = "Resume Sim"
            start_stop_color = GRAY
        elif simulation_running:
            start_stop_text = "Pause Sim"
            start_stop_color = ORANGE
            start_text_color = WHITE
        else:
            start_stop_text = "Resume Sim"
            start_stop_color = GREEN
    else:
        start_stop_text = "Start Sim"
        start_stop_color = GREEN

    pygame.draw.rect(screen, start_stop_color, start_button_rect)
    start_text_render = FONT_MEDIUM.render(start_stop_text, True, start_text_color)
    screen.blit(start_text_render, (start_button_rect.x + 10, start_button_rect.y + 5))

    can_step_next = (
        step_by_step_mode
        and simulation_game_status == "playing"
        and (current_step_index < len(simulation_steps_data) - 1)
    )
    pygame.draw.rect(screen, BLUE if can_step_next else GRAY, step_button_rect)
    step_text = FONT_MEDIUM.render("Next Step", True, WHITE if can_step_next else BLACK)
    screen.blit(step_text, (step_button_rect.x + 10, step_button_rect.y + 5))

    pygame.draw.rect(
        screen, LIGHT_BLUE if step_by_step_mode else GRAY, step_mode_button_rect
    )
    step_mode_text = FONT_MEDIUM.render(
        f"Step Mode: {'ON' if step_by_step_mode else 'OFF'}", True, BLACK
    )
    screen.blit(
        step_mode_text, (step_mode_button_rect.x + 10, step_mode_button_rect.y + 5)
    )

    status_y_start = step_mode_button_rect.bottom + y_spacing + 20
    display_step = max(0, current_step_index)
    step_num_text = FONT_MEDIUM.render(f"Step: {display_step}", True, BLACK)
    screen.blit(step_num_text, (ui_start_x, status_y_start))

    score_text = FONT_MEDIUM.render(f"Score: {simulation_score}", True, BLACK)
    screen.blit(score_text, (ui_start_x, status_y_start + 30))
    time_text = FONT_MEDIUM.render(f"Time: {simulation_time_taken}", True, BLACK)
    screen.blit(time_text, (ui_start_x, status_y_start + 60))

    game_status_display = simulation_game_status.replace("_", " ").capitalize()
    status_text_render = FONT_MEDIUM.render(
        f"Status: {game_status_display}", True, BLACK
    )
    screen.blit(status_text_render, (ui_start_x, status_y_start + 90))

    if simulation_percepts_current and simulation_game_status not in ["init", "error"]:
        p_text = f"Percepts: S({simulation_percepts_current[0]}) B({simulation_percepts_current[1]}) G({simulation_percepts_current[2]})"
        percepts_display = FONT_MEDIUM.render(p_text, True, BLACK)
        screen.blit(percepts_display, (ui_start_x, status_y_start + 120))

    log_y_start = status_y_start + 150
    grid_bottom = GRID_MARGIN_Y + WORLD_DIM * CELL_SIZE + 20
    if log_y_start < grid_bottom:
        log_y_start = grid_bottom

    log_area_height = SCREEN_HEIGHT - log_y_start - 10
    max_visible_lines = log_area_height // (FONT_SMALL.get_height() + 2)

    for i, msg in enumerate(message_log[:max_visible_lines]):
        msg_render = FONT_SMALL.render(msg, True, BLACK)
        screen.blit(
            msg_render, (GRID_MARGIN_X, log_y_start + i * (FONT_SMALL.get_height() + 2))
        )

    return reset_button_rect, start_button_rect, step_button_rect, step_mode_button_rect


# --- Game Logic Functions ---
def initialize_simulation():
    global current_step_index, simulation_agent_pos, simulation_agent_path
    global simulation_score, simulation_time_taken, simulation_game_status
    global simulation_percepts_current, simulation_running, message_log
    global simulation_steps_data, simulation_wumpus_status, simulation_wumpus_location
    global safe_locations, maybe_wumpus_locations, no_wumpus_locations, maybe_pit_locations, no_pit_locations
    global visited_locations

    add_message("--- Initializing Simulation ---")
    if not run_prolog_script():
        add_message("Initialization failed: Could not run Prolog script.")
        simulation_game_status = "error"
        simulation_steps_data = []
        message_log = [msg for msg in message_log if "ERROR" in msg or "Welcome" in msg]
        return

    if not load_and_parse_kb_log():
        add_message(f"Initialization failed: Could not parse '{KB_FILE_PATH}'.")
        simulation_game_status = "error"
        message_log = [msg for msg in message_log if "ERROR" in msg or "Welcome" in msg]
        return

    current_step_index = -1
    simulation_agent_pos = list(initial_agent_pos_prolog)
    simulation_agent_path = [list(initial_agent_pos_prolog)]
    simulation_score = 0
    simulation_time_taken = 0
    simulation_percepts_current = None
    simulation_running = False
    simulation_game_status = "ready"
    simulation_wumpus_status = "alive"
    simulation_wumpus_location = list(wumpus_location_prolog)
    safe_locations.clear()
    maybe_wumpus_locations.clear()
    no_wumpus_locations.clear()
    maybe_pit_locations.clear()
    no_pit_locations.clear()
    visited_locations = [list(initial_agent_pos_prolog)]

    add_message(
        f"Initialization complete. Agent at {simulation_agent_pos}. Press 'Start Sim'."
    )
    message_log = message_log[-MAX_LOG_LINES:]


def handle_start_press():
    global current_step_index, simulation_game_status, simulation_percepts_current
    global simulation_running, simulation_score, simulation_time_taken, last_auto_step_time
    global simulation_agent_pos, simulation_wumpus_status, simulation_wumpus_location
    global safe_locations, maybe_wumpus_locations, no_wumpus_locations, maybe_pit_locations, no_pit_locations

    if not simulation_steps_data:
        add_message("Error: No simulation data loaded. Cannot start.")
        return

    first_round_data = simulation_steps_data[0]
    initial_percepts = first_round_data.get("percepts")
    initial_messages = first_round_data.get("messages", [])
    initial_safe_locations = first_round_data.get("safe_locations", [])
    initial_maybe_wumpus = first_round_data.get("maybe_wumpus_locations", [])
    initial_no_wumpus = first_round_data.get("no_wumpus_locations", [])
    initial_maybe_pit = first_round_data.get("maybe_pit_locations", [])
    initial_no_pit = first_round_data.get("no_pit_locations", [])
    initial_wumpus_status = first_round_data.get("wumpus_status", "alive")
    initial_wumpus_location = first_round_data.get(
        "wumpus_location", simulation_wumpus_location
    )

    if initial_percepts is None:
        add_message("Error: Missing percept data for the first round in kb.txt.")
        simulation_game_status = "error"
        return

    current_step_index = 0
    simulation_agent_pos = list(first_round_data["start_location"])
    simulation_score = 0
    simulation_time_taken = 0
    simulation_percepts_current = initial_percepts
    simulation_game_status = "playing"
    simulation_wumpus_status = initial_wumpus_status
    simulation_wumpus_location = initial_wumpus_location
    safe_locations[:] = initial_safe_locations
    maybe_wumpus_locations[:] = initial_maybe_wumpus
    no_wumpus_locations[:] = initial_no_wumpus
    maybe_pit_locations[:] = initial_maybe_pit
    no_pit_locations[:] = initial_no_pit

    add_message(
        f"Step 0: Agent at {simulation_agent_pos}. Percepts: {initial_percepts}. Score: {simulation_score}, Time: {simulation_time_taken}. Status: playing"
    )
    for msg in initial_messages:
        if not msg.startswith("I'm going to:"):
            add_message(msg)

    if not step_by_step_mode:
        add_message("Simulation started (Auto Mode).")
        simulation_running = True
        last_auto_step_time = pygame.time.get_ticks()
    else:
        add_message("Simulation started (Step Mode). Press 'Next Step' to proceed.")
        simulation_running = False


def advance_simulation_step():
    global current_step_index, simulation_agent_pos, simulation_agent_path
    global simulation_score, simulation_time_taken, simulation_game_status
    global simulation_percepts_current, simulation_running
    global simulation_wumpus_status, simulation_wumpus_location
    global safe_locations, maybe_wumpus_locations, no_wumpus_locations, maybe_pit_locations, no_pit_locations

    if simulation_game_status != "playing":
        simulation_running = False
        return False

    if current_step_index + 1 >= len(simulation_steps_data):
        add_message("End of simulation data reached.")
        simulation_game_status = (
            simulation_steps_data[current_step_index]["end_status"]
            if current_step_index >= 0
            else "finished"
        )
        if simulation_game_status == "playing":
            simulation_game_status = "finished"
        simulation_running = False
        return False

    current_step_index += 1
    round_data = simulation_steps_data[current_step_index]
    current_pos = round_data.get("start_location")
    current_percepts = round_data.get("percepts", ["?", "?", "?"])
    current_score = round_data.get("score")
    current_time = round_data.get("time")
    current_status = round_data.get("end_status", "playing")
    current_wumpus_status = round_data.get("wumpus_status", simulation_wumpus_status)
    current_wumpus_location = round_data.get(
        "wumpus_location", simulation_wumpus_location
    )
    current_messages = round_data.get("messages", [])
    current_safe_locations = round_data.get("safe_locations", [])
    current_maybe_wumpus = round_data.get("maybe_wumpus_locations", [])
    current_no_wumpus = round_data.get("no_wumpus_locations", [])
    current_maybe_pit = round_data.get("maybe_pit_locations", [])
    current_no_pit = round_data.get("no_pit_locations", [])

    if (
        current_pos is None
        or current_percepts is None
        or current_score is None
        or current_time is None
    ):
        add_message(
            f"Error: Missing critical data for round index {current_step_index}. Halting."
        )
        print(f"Debug data round {current_step_index}: {round_data}")
        simulation_game_status = "error"
        simulation_running = False
        return False

    add_message(
        f"Step {current_step_index}: Agent at {current_pos}. Percepts: {current_percepts}. Score: {current_score}, Time: {current_time}. Status: {current_status}"
    )
    for msg in current_messages:
        add_message(msg)

    simulation_agent_pos = list(current_pos)
    simulation_percepts_current = current_percepts
    simulation_score = current_score
    simulation_time_taken = current_time
    simulation_game_status = current_status
    simulation_wumpus_status = current_wumpus_status
    simulation_wumpus_location = current_wumpus_location
    safe_locations[:] = current_safe_locations
    maybe_wumpus_locations[:] = current_maybe_wumpus
    no_wumpus_locations[:] = current_no_wumpus
    maybe_pit_locations[:] = current_maybe_pit
    no_pit_locations[:] = current_no_pit

    if current_step_index > 0:
        prev_pos = simulation_steps_data[current_step_index - 1]["start_location"]
        if current_pos != prev_pos:
            simulation_agent_path.append(list(current_pos))

    if simulation_game_status != "playing":
        simulation_running = False
        add_message(f"--- Simulation {simulation_game_status.upper()} ---")
        return False

    return True


# --- Main Game Loop ---
async def main():
    global simulation_running, step_by_step_mode, message_log, current_step_index, last_auto_step_time
    running = True
    clock = pygame.time.Clock()
    auto_step_delay = 700

    initialize_simulation()

    ui_button_rects = None

    while running:
        current_time_ms = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and ui_button_rects
            ):
                reset_btn_rect, start_btn_rect, step_btn_rect, step_mode_btn_rect = (
                    ui_button_rects
                )
                if reset_btn_rect.collidepoint(mouse_pos):
                    add_message("Reset button clicked.")
                    message_log = [
                        "Welcome to Wumpus World (Simulated)! Please click 'Start Sim' to begin."
                    ]
                    initialize_simulation()
                elif start_btn_rect.collidepoint(mouse_pos):
                    if simulation_game_status == "ready":
                        handle_start_press()
                    elif simulation_game_status == "playing":
                        if step_by_step_mode:
                            add_message("Use 'Next Step' button in Step Mode.")
                        elif simulation_running:
                            add_message("Pause Simulation button clicked.")
                            simulation_running = False
                        else:
                            add_message("Resume Simulation button clicked.")
                            simulation_running = True
                            last_auto_step_time = current_time_ms
                    else:
                        add_message("Start Sim button clicked (Resetting).")
                        message_log = [
                            "Welcome to Wumpus World (Simulated)! Please click 'Start Sim' to begin."
                        ]
                        initialize_simulation()
                elif step_btn_rect.collidepoint(mouse_pos):
                    if step_by_step_mode and simulation_game_status == "playing":
                        add_message("Next Step button clicked.")
                        if advance_simulation_step():
                            add_message(f"Advanced to step {current_step_index}.")
                        else:
                            add_message("Cannot advance further.")
                elif step_mode_btn_rect.collidepoint(mouse_pos):
                    step_by_step_mode = not step_by_step_mode
                    add_message(
                        f"Step Mode toggled to {'ON' if step_by_step_mode else 'OFF'}."
                    )
                    if step_by_step_mode and simulation_running:
                        simulation_running = False
                        add_message("Simulation paused due to Step Mode ON.")
                    elif not step_by_step_mode and simulation_game_status == "playing":
                        simulation_running = True
                        last_auto_step_time = current_time_ms
                        add_message("Simulation resumed in Auto Mode.")

        if (
            simulation_running
            and not step_by_step_mode
            and simulation_game_status == "playing"
        ):
            if current_time_ms - last_auto_step_time >= auto_step_delay:
                if advance_simulation_step():
                    last_auto_step_time = current_time_ms
                else:
                    add_message("Simulation stopped: End of steps or game over.")
                    simulation_running = False

        screen.fill(WHITE)
        draw_grid()
        draw_world_elements()
        draw_agent_path()
        draw_action_effects()
        draw_agent()
        draw_percepts_at_agent_location()
        ui_button_rects = draw_ui_elements()

        pygame.display.flip()
        clock.tick(60)
        if platform.system() == "Emscripten":
            await asyncio.sleep(1.0 / 60)
        else:
            await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
