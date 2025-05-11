import pygame
from pyswip import Prolog, Functor, Variable, Atom  # Cần thêm Functor, Variable, Atom
import os

# --- Pygame Setup ---
pygame.init()
pygame.font.init()

# Screen dimensions
SCREEN_WIDTH = 950  # Increased width for more UI elements
SCREEN_HEIGHT = 700  # Increased height for message log
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Wumpus World")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GOLD_COLOR = (255, 215, 0)
LIGHT_BLUE = (173, 216, 230)

# Fonts
FONT_SMALL = pygame.font.SysFont("arial", 18)  # Adjusted font size
FONT_MEDIUM = pygame.font.SysFont("arial", 22)
FONT_LARGE = pygame.font.SysFont("arial", 28)

# Grid settings
CELL_SIZE = 70  # Slightly smaller cells if needed for larger world
GRID_MARGIN_X = 50
GRID_MARGIN_Y = 50
WORLD_DIM = 4  # Default, will be updated from Prolog


# --- Asset Loading ---
def load_image(name, size=(CELL_SIZE - 10, CELL_SIZE - 10)):
    try:
        # Versuche, das Bild aus einem 'images'-Unterverzeichnis zu laden
        path = os.path.join("images", name)
        if not os.path.exists(path):  # Fallback auf das aktuelle Verzeichnis
            path = name
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


agent_img = None
wumpus_img = None
pit_img = None
gold_img = None
stench_img = None
breeze_img = None
start_node_img = None  # For marking start


def load_all_images():
    global agent_img, wumpus_img, pit_img, gold_img, stench_img, breeze_img, start_node_img
    entity_size = (int(CELL_SIZE * 0.8), int(CELL_SIZE * 0.8))
    percept_icon_size = (int(CELL_SIZE * 0.4), int(CELL_SIZE * 0.4))

    agent_img = load_image("../image/agent.png", entity_size)
    wumpus_img = load_image("../image/wumpus.png", entity_size)
    pit_img = load_image("../image/pit.png", entity_size)
    gold_img = load_image("../image/gold.png", entity_size)
    stench_img = load_image("../image/stench.png", percept_icon_size)
    breeze_img = load_image("../image/breeze.png", percept_icon_size)
    # Placeholder for start node, can be a simple circle or text
    surf = pygame.Surface(entity_size, pygame.SRCALPHA)  # Transparent surface
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

# --- Prolog Interface ---
prolog = Prolog()
PROLOG_FILE_LOADED = False
try:
    prolog.consult("wumpus_agent.pl")
    PROLOG_FILE_LOADED = True
    print("Prolog file wumpus_agent.pl loaded successfully.")
except Exception as e:
    print(f"Could not consult Prolog file: {e}")

    class DummyProlog:
        def query(self, q_str):
            print(f"DummyProlog: Would query '{q_str}'")
            return []

        def assertz(self, fact):
            print(f"DummyProlog: Would assert '{fact}'")

        def retractall(self, fact):
            print(f"DummyProlog: Would retractall '{fact}'")

    prolog = DummyProlog()

# --- Game State Variables ---
initial_agent_pos_prolog = [1, 1]  # To mark the start cell
agent_pos_prolog = [1, 1]
agent_path = []
pit_locations_prolog = []
wumpus_location_prolog = []
gold_location_prolog = []
visited_list_for_display = []  # Cells confirmed OK by agent

score = 0
time_taken = 0
game_status = "init"  # init, playing, won, lost_wumpus, lost_pit, error, stuck_or_error
percepts_current = []
visited_list_prolog_kb = (
    [1,1]
)  # This is the KB's VisitedList, a list of [X,Y] Prolog coords

step_by_step_mode = False
simulation_running = False  # True when auto-playing or game is active
message_log = ["Welcome to Wumpus World!"]
MAX_LOG_LINES = 10


# --- Helper Functions ---
def prolog_to_grid_coords(prolog_x, prolog_y):
    # Prolog [X,Y] (X:col from left, Y:row from bottom, 1-indexed)
    # Pygame grid [col, row] (col:from left, row:from top, 0-indexed)
    grid_col = prolog_x - 1
    grid_row = WORLD_DIM - prolog_y  # Y is inverted
    return grid_col, grid_row


def grid_to_screen_coords(grid_col, grid_row):
    screen_x = (
        GRID_MARGIN_X + grid_col * CELL_SIZE + (CELL_SIZE - agent_img.get_width()) // 2
    )  # Center image
    screen_y = (
        GRID_MARGIN_Y + grid_row * CELL_SIZE + (CELL_SIZE - agent_img.get_height()) // 2
    )
    return screen_x, screen_y


def add_message(msg):
    print(f"UI_LOG: {msg}")  # Also print to console for easier debugging
    message_log.insert(0, msg)  # Add to the beginning
    if len(message_log) > MAX_LOG_LINES:
        message_log.pop()


# --- Drawing Functions ---
def draw_grid():
    for r_idx_pygame in range(WORLD_DIM):  # Pygame row index (0 from top)
        for c_idx_pygame in range(WORLD_DIM):  # Pygame col index (0 from left)
            rect = pygame.Rect(
                GRID_MARGIN_X + c_idx_pygame * CELL_SIZE,
                GRID_MARGIN_Y + r_idx_pygame * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE,
            )
            pygame.draw.rect(screen, BLACK, rect, 1)

            prolog_x = c_idx_pygame + 1
            prolog_y = (
                WORLD_DIM - r_idx_pygame
            )  # Convert Pygame row back to Prolog Y (from bottom)

            # Display cell coordinates (Prolog style)
            coord_text = FONT_SMALL.render(f"({prolog_x},{prolog_y})", True, GRAY)
            screen.blit(coord_text, (rect.x + 5, rect.y + 5))

            # Mark visited_list_for_display cells (OK cells explored by agent)
            if [prolog_x, prolog_y] in visited_list_for_display:
                # Draw a subtle background for visited cells
                visited_overlay = pygame.Surface(
                    (CELL_SIZE - 2, CELL_SIZE - 2), pygame.SRCALPHA
                )
                visited_overlay.fill((0, 255, 0, 50))  # Light green, semi-transparent
                screen.blit(visited_overlay, (rect.x + 1, rect.y + 1))


def draw_world_elements():
    # Draw Pits (known to UI, actual locations)
    for p_x, p_y in pit_locations_prolog:
        col, row = prolog_to_grid_coords(p_x, p_y)
        s_x, s_y = grid_to_screen_coords(col, row)
        screen.blit(pit_img, (s_x, s_y))

    # Draw Wumpus
    if wumpus_location_prolog:
        w_x, w_y = wumpus_location_prolog
        col, row = prolog_to_grid_coords(w_x, w_y)
        s_x, s_y = grid_to_screen_coords(col, row)
        screen.blit(wumpus_img, (s_x, s_y))

    # Draw Gold
    if gold_location_prolog:
        g_x, g_y = gold_location_prolog
        col, row = prolog_to_grid_coords(g_x, g_y)
        s_x, s_y = grid_to_screen_coords(col, row)
        screen.blit(gold_img, (s_x, s_y))

    # Mark start node
    if initial_agent_pos_prolog:
        col, row = prolog_to_grid_coords(
            initial_agent_pos_prolog[0], initial_agent_pos_prolog[1]
        )
        s_x, s_y = grid_to_screen_coords(col, row)
        screen.blit(start_node_img, (s_x, s_y))


def draw_agent_path():
    if len(agent_path) > 1:
        points_screen = []
        for p_pos_prolog in agent_path:
            col, row = prolog_to_grid_coords(p_pos_prolog[0], p_pos_prolog[1])
            # Path center of cell
            center_x = GRID_MARGIN_X + col * CELL_SIZE + CELL_SIZE // 2
            center_y = GRID_MARGIN_Y + row * CELL_SIZE + CELL_SIZE // 2
            points_screen.append((center_x, center_y))
        pygame.draw.lines(screen, BLUE, False, points_screen, 3)


def draw_agent():
    if agent_pos_prolog:
        col, row = prolog_to_grid_coords(agent_pos_prolog[0], agent_pos_prolog[1])
        s_x, s_y = grid_to_screen_coords(col, row)
        screen.blit(agent_img, (s_x, s_y))


def draw_percepts_at_agent_location():
    if percepts_current and agent_pos_prolog and game_status == "playing":
        # Percepts are [Stench, Breeze, Glitter]
        stench_val, breeze_val, glitter_val = [str(p) for p in percepts_current]

        col_agent, row_agent = prolog_to_grid_coords(
            agent_pos_prolog[0], agent_pos_prolog[1]
        )
        base_screen_x, base_screen_y = grid_to_screen_coords(col_agent, row_agent)

        # Position percept icons within the cell, e.g., top-right corner of cell
        icon_start_x = (
            GRID_MARGIN_X
            + col_agent * CELL_SIZE
            + CELL_SIZE
            - stench_img.get_width()
            - 2
        )
        icon_y_offset = GRID_MARGIN_Y + row_agent * CELL_SIZE + 2

        if stench_val == "yes":
            screen.blit(stench_img, (icon_start_x, icon_y_offset))
            icon_y_offset += stench_img.get_height() + 1
        if breeze_val == "yes":
            screen.blit(breeze_img, (icon_start_x, icon_y_offset))
            # icon_y_offset += breeze_img.get_height() + 1 # Not needed if glitter not shown as icon
        # Glitter is usually represented by the Gold image itself if agent is on it.
        # Or if agent perceives glitter from adjacent cell (not standard Wumpus).


def draw_ui_elements():
    ui_start_x = GRID_MARGIN_X + WORLD_DIM * CELL_SIZE + 30
    button_width = 180  # Wider buttons
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

    # Reset Button
    pygame.draw.rect(screen, RED, reset_button_rect)
    reset_text = FONT_MEDIUM.render("Reset Game", True, WHITE)
    screen.blit(reset_text, (reset_button_rect.x + 10, reset_button_rect.y + 5))

    # Start/Stop Button
    start_stop_text = "Start Agent"
    start_stop_color = GREEN
    if simulation_running and game_status == "playing":
        start_stop_text = "Pause Agent"
        start_stop_color = RED
    elif not simulation_running and game_status == "playing":
        start_stop_text = "Resume Agent"
        start_stop_color = GREEN
    elif game_status != "init" and game_status != "playing":  # Game over or error
        start_stop_text = "Start Agent"  # Will trigger reset
        start_stop_color = GREEN

    pygame.draw.rect(screen, start_stop_color, start_button_rect)
    start_text_render = FONT_MEDIUM.render(start_stop_text, True, BLACK)
    screen.blit(start_text_render, (start_button_rect.x + 10, start_button_rect.y + 5))

    # Next Step Button
    pygame.draw.rect(
        screen,
        BLUE if step_by_step_mode and game_status == "playing" else GRAY,
        step_button_rect,
    )
    step_text = FONT_MEDIUM.render(
        "Next Step",
        True,
        WHITE if step_by_step_mode and game_status == "playing" else BLACK,
    )
    screen.blit(step_text, (step_button_rect.x + 10, step_button_rect.y + 5))

    # Step Mode Toggle Button
    pygame.draw.rect(
        screen, LIGHT_BLUE if step_by_step_mode else GRAY, step_mode_button_rect
    )
    step_mode_text = FONT_MEDIUM.render(
        f"Step Mode: {'ON' if step_by_step_mode else 'OFF'}", True, BLACK
    )
    screen.blit(
        step_mode_text, (step_mode_button_rect.x + 10, step_mode_button_rect.y + 5)
    )

    # Status Text
    status_y_start = step_mode_button_rect.bottom + y_spacing + 20
    score_text = FONT_MEDIUM.render(f"Score: {score}", True, BLACK)
    screen.blit(score_text, (ui_start_x, status_y_start))
    time_text = FONT_MEDIUM.render(f"Time: {time_taken}", True, BLACK)
    screen.blit(time_text, (ui_start_x, status_y_start + 30))
    game_status_display = game_status
    if game_status == "stuck_or_error":
        game_status_display = "Agent Stuck/Error"
    status_text_render = FONT_MEDIUM.render(
        f"Status: {game_status_display.capitalize()}", True, BLACK
    )
    screen.blit(status_text_render, (ui_start_x, status_y_start + 60))

    if percepts_current:
        p_text_vals = [str(p) for p in percepts_current]
        p_text = (
            f"Percepts: S({p_text_vals[0]}) B({p_text_vals[1]}) G({p_text_vals[2]})"
        )
        percepts_display = FONT_MEDIUM.render(p_text, True, BLACK)
        screen.blit(percepts_display, (ui_start_x, status_y_start + 90))

    # Message Log
    log_y_start = GRID_MARGIN_Y + WORLD_DIM * CELL_SIZE + 20
    if log_y_start < status_y_start + 120:  # Ensure log is below other UI
        log_y_start = status_y_start + 120

    for i, msg in enumerate(message_log):
        msg_render = FONT_SMALL.render(msg, True, BLACK)
        screen.blit(
            msg_render, (GRID_MARGIN_X, log_y_start + i * (FONT_SMALL.get_height() + 2))
        )

    return reset_button_rect, start_button_rect, step_button_rect, step_mode_button_rect


# --- Game Logic Functions ---
def format_prolog_list(py_list):
    """Formats a Python list of lists into a Prolog-compatible string."""
    if not py_list:
        return "[]"
    return "[" + ",".join([f"[{x},{y}]" for x, y in py_list]) + "]"


# def parse_prolog_list_of_lists(prolog_term):
#     """Parses Prolog list term (potentially from pyswip) into Python list of lists."""
#     if isinstance(prolog_term, list):  # Already a Python list (pyswip might do this)
#         # Ensure sub-elements are also lists if they represent coordinates
#         return [
#             (
#                 [int(c.value) if isinstance(c, Atom) else int(c) for c in pair]
#                 if isinstance(pair, list)
#                 else pair
#             )
#             for pair in prolog_term
#         ]
#     return []  # Fallback or add more robust parsing if needed


def parse_prolog_list_of_coords(prolog_term):  # Đổi tên để rõ ràng hơn
    """
    Parses Prolog list term (potentially from pyswip) into Python list of coordinate lists.
    E.g., [[1,2], [3,4]] or Atom representation of such.
    """
    if not isinstance(prolog_term, list):
        # Handle cases where prolog_term might be a single Atom representing an empty list like '[]'
        if isinstance(prolog_term, Atom) and str(prolog_term) == "[]":
            return []
        add_message(
            f"Warning: parse_prolog_list_of_coords expected list, got {type(prolog_term)}: {prolog_term}"
        )
        return []  # Or raise error

    parsed_coords_list = []
    for pair in prolog_term:
        if isinstance(pair, list) and len(pair) == 2:
            try:
                x = int(pair[0].value) if isinstance(pair[0], Atom) else int(pair[0])
                y = int(pair[1].value) if isinstance(pair[1], Atom) else int(pair[1])
                parsed_coords_list.append([x, y])
            except ValueError as e:
                add_message(f"Error parsing coordinate pair {pair}: {e}")
                # Decide: skip this pair, add a placeholder, or error out
                # For now, skip invalid pair
            except AttributeError as e:  # If .value access fails for non-Atom non-int
                add_message(f"Error accessing value in coordinate pair {pair}: {e}")

        elif (
            isinstance(pair, Atom) and str(pair) == "[]"
        ):  # Handles empty list as an element if prolog returns that
            pass  # Effectively skips it if it's not a coordinate pair
        # else:
        # add_message(f"Warning: Unexpected item in coordinate list: {pair}")
    return parsed_coords_list


def parse_prolog_single_coord(prolog_term):
    """Parses a single Prolog coordinate pair e.g. [1,2]"""
    if isinstance(prolog_term, list) and len(prolog_term) == 2:
        try:
            x = (
                int(prolog_term[0].value)
                if isinstance(prolog_term[0], Atom)
                else int(prolog_term[0])
            )
            y = (
                int(prolog_term[1].value)
                if isinstance(prolog_term[1], Atom)
                else int(prolog_term[1])
            )
            return [x, y]
        except (ValueError, AttributeError) as e:
            add_message(f"Error parsing single coordinate {prolog_term}: {e}")
            return None  # Indicate failure
    add_message(
        f"Warning: parse_prolog_single_coord expected list of 2, got {prolog_term}"
    )
    return None


def parse_prolog_percepts(prolog_term):
    """Parses Prolog percept list (e.g., [no,yes,no]) into Python list of strings."""
    if isinstance(prolog_term, list):
        # Pyswip might return list of Atoms or already list of strings if atoms are simple
        return [str(p.value) if isinstance(p, Atom) else str(p) for p in prolog_term]
    add_message(f"Warning: parse_prolog_percepts expected list, got {prolog_term}")
    return []  # Fallback

def update_percepts():
    global percepts_current
    if PROLOG_FILE_LOADED and game_status == "playing":
        try:
            query_str = f"make_percept_sentence(Percepts)."
            results = list(prolog.query(query_str))
            if results:
                percepts_current = parse_prolog_percepts(results[0]["Percepts"])
            else:
                percepts_current = ["no", "no", "no"]
        except Exception as e:
            add_message(f"Error updating percepts: {e}")
            percepts_current = ["no", "no", "no"]
            
def initialize_game_state():
    global agent_pos_prolog, score, time_taken, game_status, visited_list_prolog_kb, agent_path, percepts_current
    global WORLD_DIM, pit_locations_prolog, wumpus_location_prolog, gold_location_prolog, initial_agent_pos_prolog
    global simulation_running, visited_list_for_display

    add_message("Initializing game from Prolog...")
    if not PROLOG_FILE_LOADED:
        add_message("Prolog file not loaded. Cannot initialize.")
        game_status = "error"
        return

    try:
        query_result = list(
            prolog.query("initialize_game_for_ui(IAL, IS, IT, WS, PitsList, GL, WL).")
        )
        if query_result:
            res = query_result[0]
            ial_parsed = parse_prolog_single_coord(res["IAL"])
            gl_parsed = parse_prolog_single_coord(res["GL"])
            wl_parsed = parse_prolog_single_coord(res["WL"])

            if not ial_parsed:
                add_message("Error: Invalid Initial Agent Location from Prolog.")
                game_status = "error"
                return

            initial_agent_pos_prolog = ial_parsed
            agent_pos_prolog = list(ial_parsed)
            score = int(res["IS"])
            time_taken = int(res["IT"])
            WORLD_DIM = int(res["WS"])
            pit_locations_prolog = parse_prolog_list_of_coords(res["PitsList"])
            gold_location_prolog = gl_parsed
            wumpus_location_prolog = wl_parsed

            game_status = "playing"
            visited_list_prolog_kb = []
            visited_list_for_display = [list(agent_pos_prolog)]
            agent_path = [list(agent_pos_prolog)]
            percepts_current = ["no", "no", "no"]
            add_message(
                f"Game initialized. Agent at {agent_pos_prolog}. World: {WORLD_DIM}x{WORLD_DIM}"
            )
            simulation_running = False  # Wait for user to click Start
        else:
            add_message("Prolog init query failed: No results returned.")
            game_status = "error"
    except Exception as e:
        add_message(f"Prolog error during init: {e}")
        game_status = "error"


def execute_one_agent_step():
    global agent_pos_prolog, score, time_taken, game_status, visited_list_prolog_kb, percepts_current, agent_path
    global simulation_running, visited_list_for_display

    if game_status != "playing":
        add_message(f"Cannot step, game status: {game_status}")
        simulation_running = False
        return

    if not PROLOG_FILE_LOADED:
        add_message("Prolog file not loaded. Cannot step.")
        game_status = "error"
        simulation_running = False
        return

    formatted_visited_kb = format_prolog_list(visited_list_prolog_kb)
    query_str = f"run_one_agent_step({formatted_visited_kb}, NextAL, NVL_KB, P_Out, S_Out, T_Out, Status_Out)."
    add_message(f"Python -> Prolog Query: {query_str}")

    try:
        results = list(prolog.query(query_str))
        if results:
            res = results[0]
            add_message(f"Debug: Prolog results: NextAL={res['NextAL']}, S_Out={res['S_Out']}, T_Out={res['T_Out']}, Status={res['Status_Out']}")  # Debug chi tiết
            prev_agent_pos = list(agent_pos_prolog)

            # Parse NextAL
            next_al_parsed = parse_prolog_single_coord(res["NextAL"])
            if next_al_parsed is None:
                add_message(f"ERROR: Prolog returned invalid NextAL: {res['NextAL']}")
                game_status = "stuck_or_error"
                simulation_running = False
                return
            agent_pos_prolog = next_al_parsed
            update_percepts()

            # Parse NVL_KB
            visited_list_prolog_kb = parse_prolog_list_of_coords(res["NVL_KB"])

            # Update score and time
            try:
                score = int(res["S_Out"])
            except (ValueError, TypeError) as e:
                add_message(f"ERROR: Invalid S_Out from Prolog: {res['S_Out']} - {e}")
                score = score - 1 if game_status == "playing" else score
            try:
                time_taken = int(res["T_Out"])
            except (ValueError, TypeError) as e:
                add_message(f"ERROR: Invalid T_Out from Prolog: {res['T_Out']} - {e}")
                time_taken = time_taken + 1 if game_status == "playing" else time_taken

            new_game_status = str(res["Status_Out"])

            # Update visited list and path
            if agent_pos_prolog not in visited_list_for_display:
                visited_list_for_display.append(list(agent_pos_prolog))
            if agent_pos_prolog != prev_agent_pos:
                agent_path.append(list(agent_pos_prolog))

            add_message(
                f"Agent moved from {prev_agent_pos} to {agent_pos_prolog}. Status: {new_game_status}, Path length: {len(agent_path)}"
            )
            add_message(
                f"Percepts: {percepts_current}. KB Visited: {len(visited_list_prolog_kb)} cells."
            )
            game_status = new_game_status

            if game_status != "playing":
                simulation_running = False
                if game_status == "won":
                    add_message(f"AGENT WON! Found the Gold! Score: {score}, Time: {time_taken}, Steps: {len(agent_path)-1}")
                elif game_status == "lost_wumpus":
                    add_message("AGENT LOST! Eaten by Wumpus.")
                elif game_status == "lost_pit":
                    add_message("AGENT LOST! Fell into a Pit.")
                elif game_status == "stuck_or_error":
                    add_message("Agent is stuck or Prolog logic error.")
        else:
            add_message("Prolog step failed: No results from query.")
            game_status = "stuck_or_error"
            simulation_running = False
    except Exception as e:
        add_message(f"Prolog error during step: {e}")
        game_status = "stuck_or_error"
        simulation_running = False



# --- Main Game Loop ---
running = True
clock = pygame.time.Clock()
auto_step_delay = 700  # milliseconds
last_auto_step_time = 0

# Load initial world state for display, but don't start simulation
initialize_game_state()
if game_status == "error":
    add_message("Critical error on initial load. Check Prolog file and paths.")

while running:
    current_time_ms = pygame.time.get_ticks()
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            reset_btn_rect, start_btn_rect, step_btn_rect, step_mode_btn_rect = (
                ui_button_rects
            )

            if reset_btn_rect.collidepoint(mouse_pos):
                add_message("Reset button clicked.")
                simulation_running = False
                step_by_step_mode = False
                initialize_game_state()

            elif start_btn_rect.collidepoint(mouse_pos):
                if game_status != "playing":  # If game over/error/init, (re)start
                    add_message("Start Agent button clicked (game not playing).")
                    initialize_game_state()
                    if game_status == "playing":
                        simulation_running = True
                        if step_by_step_mode:
                            simulation_running = False
                elif simulation_running:  # Pause
                    add_message("Pause Agent button clicked.")
                    simulation_running = False
                else:  # Resume
                    add_message("Resume Agent button clicked.")
                    if not step_by_step_mode:
                        simulation_running = True

            elif step_btn_rect.collidepoint(mouse_pos):
                if step_by_step_mode and game_status == "playing":
                    add_message("Next Step button clicked.")
                    execute_one_agent_step()
                elif not step_by_step_mode:
                    add_message("Enable Step Mode to use 'Next Step'.")
                elif game_status != "playing":
                    add_message("Game not 'playing'. Reset or Start agent.")

            elif step_mode_btn_rect.collidepoint(mouse_pos):
                step_by_step_mode = not step_by_step_mode
                add_message(
                    f"Step-by-step mode {'ON' if step_by_step_mode else 'OFF'}."
                )
                if step_by_step_mode:
                    simulation_running = False

    # Auto-step logic
    if simulation_running and not step_by_step_mode and game_status == "playing":
        if current_time_ms - last_auto_step_time > auto_step_delay:
            execute_one_agent_step()
            last_auto_step_time = current_time_ms

    # Drawing
    screen.fill(WHITE)
    draw_grid()
    draw_world_elements()
    draw_agent_path()
    draw_agent()
    draw_percepts_at_agent_location()
    ui_button_rects = draw_ui_elements()

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
