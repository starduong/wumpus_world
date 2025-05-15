import asyncio
import platform
import pygame
import os
import re
import subprocess
import shutil
import ast

# --- Cấu hình ---
PROLOG_EXECUTABLE = "swipl"
PROLOG_SCRIPT = os.path.join(os.path.dirname(__file__), "wumpus_agent.pl") # Cập nhật để sử dụng file Prolog của bạn
KB_FILE_PATH = os.path.join(os.path.dirname(__file__), "kb.txt")
INIT_DATA_PATH = os.path.join(os.path.dirname(__file__), "init_data.txt") # Đường dẫn đến file init_data.txt

# --- Thiết lập Pygame ---
pygame.init()
pygame.font.init()

# Kích thước màn hình
SCREEN_WIDTH = 950
SCREEN_HEIGHT = 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Wumpus World (Simulated from kb.txt)")

# Màu sắc
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
DIM_COLOR = (0, 0, 0, 150)  # Màu mờ cho các ô chưa thăm

# Font chữ
FONT_SMALL = pygame.font.SysFont("arial", 18)
FONT_MEDIUM = pygame.font.SysFont("arial", 22)
FONT_LARGE = pygame.font.SysFont("arial", 28)

# Cài đặt lưới
CELL_SIZE = 70
GRID_MARGIN_X = 50
GRID_MARGIN_Y = 50

# --- Đọc cấu hình từ init_data.txt ---
def load_init_data():
    """
    Đọc dữ liệu từ init_data.txt để lấy kích thước bản đồ, vị trí Wumpus, hố, và vàng.
    Trả về tuple (world_dim, wumpus_locations, pit_locations, gold_location).
    Nếu đọc thất bại, trả về giá trị mặc định.
    """
    global WORLD_DIM, initial_agent_pos_prolog, pit_locations_prolog, wumpus_location_prolog, gold_location_prolog
    try:
        with open(INIT_DATA_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if len(lines) != 4:
            print(f"Lỗi: init_data.txt phải có đúng 4 dòng, nhận được {len(lines)} dòng.")
            return False

        # Đọc kích thước bản đồ
        world_dim = int(lines[0].strip().rstrip("."))
        
        # Đọc danh sách vị trí Wumpus (có thể nhiều Wumpus)
        wumpus_locations = ast.literal_eval(lines[1].strip().rstrip("."))
        
        # Đọc danh sách vị trí hố
        pit_locations = ast.literal_eval(lines[2].strip().rstrip("."))
        
        # Đọc vị trí vàng
        gold_location = ast.literal_eval(lines[3].strip().rstrip("."))

        # Cập nhật các biến toàn cục
        WORLD_DIM = world_dim
        initial_agent_pos_prolog = [1, 1]  # Agent luôn bắt đầu tại [1,1]
        wumpus_location_prolog = wumpus_locations  # Danh sách các Wumpus
        pit_locations_prolog = pit_locations
        gold_location_prolog = gold_location

        print(f"Đã đọc init_data.txt: world_dim={world_dim}, wumpus={wumpus_locations}, "
              f"pit={pit_locations}, gold={gold_location}")
        return True

    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file {INIT_DATA_PATH}")
        return False
    except (ValueError, SyntaxError) as e:
        print(f"Lỗi khi phân tích init_data.txt: {e}")
        return False
    except Exception as e:
        print(f"Lỗi không xác định khi đọc init_data.txt: {e}")
        return False

# --- Thiết lập mặc định (sử dụng nếu không đọc được init_data.txt) ---
WORLD_DIM = 4
initial_agent_pos_prolog = [1, 1]
pit_locations_prolog = [[4, 4], [3, 3], [3, 1]]
wumpus_location_prolog = [[1, 3]]  # Sửa thành danh sách để hỗ trợ nhiều Wumpus
gold_location_prolog = [3, 2]

# --- Tải tài nguyên hình ảnh ---
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
    """
    Tải hình ảnh từ thư mục hoặc tạo hình ảnh thay thế nếu không tìm thấy.
    """
    try:
        path = os.path.join("image", name)
        if not os.path.exists(path):
            path = name
            if not os.path.exists(path):
                path_no_ext = os.path.splitext(name)[0]
                if os.path.exists(path_no_ext):
                    path = path_no_ext
                else:
                    print(f"Không tìm thấy file hình ảnh: {name}")
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
        print(f"Không thể tải hình ảnh: {name} - {e}")
        surface = pygame.Surface(size)
        surface.fill(GRAY)
        text = FONT_SMALL.render(name.split(".")[0][:3], True, BLACK)
        text_rect = text.get_rect(center=(size[0] // 2, size[1] // 2))
        surface.blit(text, text_rect)
        return surface
    except FileNotFoundError:
        print(f"Không tìm thấy file hình ảnh: {name}")
        surface = pygame.Surface(size)
        surface.fill(GRAY)
        text = FONT_SMALL.render(name.split(".")[0][:3], True, BLACK)
        text_rect = text.get_rect(center=(size[0] // 2, size[1] // 2))
        surface.blit(text, text_rect)
        return surface

def create_question_mark_img(size):
    """
    Tạo hình ảnh dấu chấm hỏi cho các ô có khả năng chứa Wumpus hoặc hố.
    """
    surface = pygame.Surface(size, pygame.SRCALPHA)
    text = FONT_MEDIUM.render("?", True, RED)
    text_rect = text.get_rect(center=(size[0] // 2, size[1] // 2))
    surface.blit(text, text_rect)
    return surface

def load_all_images():
    """
    Tải tất cả hình ảnh cần thiết cho giao diện.
    """
    global agent_img, wumpus_img, pit_img, gold_img, stench_img, breeze_img, glitter_img
    global start_node_img, arrow_img, safe_img, question_mark_img
    entity_size = (int(CELL_SIZE * 0.8), int(CELL_SIZE * 0.8))
    percept_icon_size = (int(CELL_SIZE * 0.4), int(CELL_SIZE * 0.4))
    safe_icon_size = (int(CELL_SIZE * 0.5), int(CELL_SIZE * 0.5))

    # Tải hình ảnh từ thư mục gốc hoặc thư mục images
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

    # Tạo hình ảnh cho điểm bắt đầu
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

# --- Biến trạng thái trò chơi ---
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
    "Welcome to Wumpus World (Simulated)! Please press 'Start Sim' to begin."
]
MAX_LOG_LINES = 15
last_auto_step_time = 0

# --- Hàm hỗ trợ ---
def prolog_to_grid_coords(prolog_x, prolog_y):
    """
    Chuyển tọa độ Prolog ([X,Y]) sang tọa độ lưới Pygame.
    """
    grid_col = prolog_x - 1
    grid_row = WORLD_DIM - prolog_y
    return grid_col, grid_row

def grid_to_screen_coords(grid_col, grid_row):
    """
    Chuyển tọa độ lưới sang tọa độ màn hình Pygame.
    """
    screen_x = (
        GRID_MARGIN_X + grid_col * CELL_SIZE + (CELL_SIZE - agent_img.get_width()) // 2
    )
    screen_y = (
        GRID_MARGIN_Y + grid_row * CELL_SIZE + (CELL_SIZE - agent_img.get_height()) // 2
    )
    return screen_x, screen_y

def add_message(msg):
    """
    Thêm thông báo vào log và giới hạn số dòng tối đa.
    """
    print(f"UI_LOG: {msg}")
    message_log.insert(0, msg)
    if len(message_log) > MAX_LOG_LINES:
        message_log.pop()

def parse_prolog_coord(coord_str):
    """
    Phân tích chuỗi tọa độ Prolog (ví dụ: [1,2]) thành list [1,2].
    """
    match = re.search(r"\[(\d+),(\d+)\]", coord_str)
    if match:
        return [int(match.group(1)), int(match.group(2))]
    return None

def parse_prolog_percepts(percept_str):
    """
    Phân tích chuỗi tri giác Prolog (ví dụ: [yes,no,yes]) thành list [stench, breeze, glitter].
    """
    match = re.search(r"\[(yes|no),(yes|no),(yes|no)\]", percept_str)
    if match:
        return [match.group(1), match.group(2), match.group(3)]
    match_vars = re.search(r"\[(_\d+),(_\d+),(_\d+)\]", percept_str)
    if match_vars:
        return ["no", "no", "no"]
    print(f"Warning: Unable to analyze perception:{percept_str}")
    return ["?", "?", "?"]

# --- Thực thi Prolog ---
def find_prolog_executable(name=PROLOG_EXECUTABLE):
    """
    Tìm đường dẫn đến chương trình Prolog (swipl).
    """
    path = shutil.which(name)
    if path:
        add_message(f"Tìm thấy Prolog: {path}")
        return path
    else:
        add_message(f"Warning: '{name}' not found in PATH. Direct call assumed.")
        return name

def run_prolog_script():
    """
    Chạy file Prolog và tạo kb.txt.
    """
    global simulation_game_status
    prolog_cmd = find_prolog_executable()
    if not prolog_cmd:
        add_message(f"ERROR: Prolog ('{PROLOG_EXECUTABLE}') not found. Please install SWI-Prolog.")
        simulation_game_status = "error"
        return False

    if not os.path.exists(PROLOG_SCRIPT):
        add_message(f"LỖI: Không tìm thấy file Prolog '{PROLOG_SCRIPT}'.")
        simulation_game_status = "error"
        return False

    command = [prolog_cmd, "-s", PROLOG_SCRIPT, "-g", "start.", "-t", "halt."]
    add_message(f"Chạy Prolog: {' '.join(command)}")
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=15, check=False
        )
        if result.returncode != 0:
            add_message(f"LỖI: Prolog thoát với mã lỗi {result.returncode}.")
            add_message("--- Prolog stdout: ---")
            add_message(result.stdout if result.stdout else "<trống>")
            add_message("--- Prolog stderr: ---")
            add_message(result.stderr if result.stderr else "<trống>")
            simulation_game_status = "error"
            if os.path.exists(KB_FILE_PATH):
                try:
                    with open(KB_FILE_PATH, "w") as f:
                        pass  # Hoặc f.write("") để rõ nghĩa hơn
                    add_message(f"Đã clear nội dung trong {KB_FILE_PATH} .")
                except OSError as e:
                    add_message(f"Cảnh báo: Không thể ghi rỗng vào {KB_FILE_PATH}: {e}")

            return False
        else:
            add_message("Thực thi Prolog thành công.")
            if not os.path.exists(KB_FILE_PATH):
                add_message(f"LỖI: Prolog hoàn tất nhưng không tạo '{KB_FILE_PATH}'.")
                add_message("--- Prolog stdout: ---")
                add_message(result.stdout if result.stdout else "<trống>")
                add_message("--- Prolog stderr: ---")
                add_message(result.stderr if result.stderr else "<trống>")
                simulation_game_status = "error"
                return False
            return True
    except FileNotFoundError:
        add_message(f"LỖI: Không tìm thấy lệnh Prolog '{prolog_cmd}'. Đã cài SWI-Prolog chưa?")
        simulation_game_status = "error"
        return False
    except subprocess.TimeoutExpired:
        add_message("LỖI: Prolog hết thời gian (quá 15 giây).")
        simulation_game_status = "error"
        return False
    except Exception as e:
        add_message(f"LỖI: Lỗi bất ngờ khi chạy Prolog: {e}")
        simulation_game_status = "error"
        return False

# --- Phân tích KB.TXT ---
def load_and_parse_kb_log(filepath=KB_FILE_PATH):
    """
    Đọc và phân tích file kb.txt để lấy dữ liệu mô phỏng.
    """
    global simulation_steps_data, simulation_wumpus_location, simulation_wumpus_status
    simulation_steps_data = []
    if not os.path.exists(filepath):
        add_message(f"LỖI: Không tìm thấy file mô phỏng {filepath}")
        return False
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except Exception as e:
        add_message(f"LỖI: Không thể đọc file {filepath}: {e}")
        return False

    rounds_text = content.split("New Round:")[1:]
    if not rounds_text:
        add_message(f"LỖI: Không tìm thấy đoạn 'New Round:' trong {filepath}")
        if not content.strip():
            add_message("File trống.")
        else:
            add_message("Nội dung file không chứa dấu 'New Round:'.")
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
                f"Cảnh báo: Dữ liệu không đầy đủ cho vòng {current_round_num+1}. Bỏ qua."
            )
            print(f"Debug: Dữ liệu bước không hoàn chỉnh: {step_info}")

    if not simulation_steps_data:
        add_message(f"LỖI: Không thể phân tích bất kỳ bước hợp lệ nào từ {filepath}")
        return False

    add_message(
        f"Đã phân tích thành công {len(simulation_steps_data)} bước từ {filepath}"
    )
    return True

# --- Hàm vẽ ---
def draw_grid():
    """
    Vẽ lưới bản đồ với tọa độ Prolog.
    """
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
            # Làm mờ các ô chưa thăm và chưa biết
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
    """
    Vẽ các thành phần của thế giới (hố, vàng, Wumpus, ô an toàn, v.v.).
    """
    if current_step_index < 0:
        # Chỉ vẽ vị trí bắt đầu ở trạng thái ban đầu
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

    # Vẽ các ô an toàn
    for safe_x, safe_y in safe_locs:
        col, row = prolog_to_grid_coords(safe_x, safe_y)
        s_x = GRID_MARGIN_X + col * CELL_SIZE + (CELL_SIZE - safe_img.get_width()) // 2
        s_y = GRID_MARGIN_Y + row * CELL_SIZE + (CELL_SIZE - safe_img.get_height()) // 2
        screen.blit(safe_img, (s_x, s_y))

    # Vẽ các ô có thể có hố
    for pit_x, pit_y in maybe_pit_locs:
        col, row = prolog_to_grid_coords(pit_x, pit_y)
        s_x, s_y = grid_to_screen_coords(col, row)
        pit_img_alpha = pit_img.copy()
        pit_img_alpha.set_alpha(128)
        screen.blit(pit_img_alpha, (s_x, s_y))
        q_x = s_x + (pit_img.get_width() - question_mark_img.get_width()) // 2
        q_y = s_y + (pit_img.get_height() - question_mark_img.get_height()) // 2
        screen.blit(question_mark_img, (q_x, q_y))

    # Vẽ vàng nếu cảm nhận lấp lánh và chưa nhặt
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

    # Vẽ các ô có thể có Wumpus
    for w_x, w_y in maybe_wumpus_locs:
        if (
            len(maybe_wumpus_locs) == 1
            and [w_x, w_y] == wumpus_location
            and wumpus_status == "alive"
        ):
            continue
        col, row = prolog_to_grid_coords(w_x, w_y)
        s_x, s_y = grid_to_screen_coords(col, row)
        wumpus_img_alpha = wumpus_img.copy()
        wumpus_img_alpha.set_alpha(128)
        screen.blit(wumpus_img_alpha, (s_x, s_y))
        q_x = s_x + (wumpus_img.get_width() - question_mark_img.get_width()) // 2
        q_y = s_y + (wumpus_img.get_height() - question_mark_img.get_height()) // 2
        screen.blit(question_mark_img, (q_x, q_y))

    # Vẽ Wumpus đã xác định
    if (
        wumpus_status == "alive"
        and wumpus_location
        and len(maybe_wumpus_locs) == 1
        and wumpus_location in maybe_wumpus_locs
    ):
        w_x, w_y = wumpus_location
        col, row = prolog_to_grid_coords(w_x, w_y)
        s_x, s_y = grid_to_screen_coords(col, row)
        screen.blit(wumpus_img, (s_x, s_y))

    # Vẽ vị trí bắt đầu
    if initial_agent_pos_prolog:
        col, row = prolog_to_grid_coords(
            initial_agent_pos_prolog[0], initial_agent_pos_prolog[1]
        )
        s_x, s_y = grid_to_screen_coords(col, row)
        if simulation_agent_pos != initial_agent_pos_prolog:
            screen.blit(start_node_img, (s_x, s_y))

def draw_agent_path():
    """
    Vẽ đường đi của agent.
    """
    if len(simulation_agent_path) > 1:
        points_screen = []
        for p_pos_prolog in simulation_agent_path:
            if isinstance(p_pos_prolog, (list, tuple)) and len(p_pos_prolog) == 2:
                col, row = prolog_to_grid_coords(p_pos_prolog[0], p_pos_prolog[1])
                center_x = GRID_MARGIN_X + col * CELL_SIZE + CELL_SIZE // 2
                center_y = GRID_MARGIN_Y + row * CELL_SIZE + CELL_SIZE // 2
                points_screen.append((center_x, center_y))
            else:
                print(f"Cảnh báo: Điểm không hợp lệ trong đường đi: {p_pos_prolog}")
        if len(points_screen) > 1:
            pygame.draw.lines(screen, BLUE, False, points_screen, 3)

def draw_action_effects():
    """
    Vẽ hiệu ứng hành động (ví dụ: bắn mũi tên).
    """
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
    """
    Vẽ agent tại vị trí hiện tại.
    """
    if simulation_agent_pos:
        col, row = prolog_to_grid_coords(
            simulation_agent_pos[0], simulation_agent_pos[1]
        )
        s_x, s_y = grid_to_screen_coords(col, row)
        screen.blit(agent_img, (s_x, s_y))

def draw_percepts_at_agent_location():
    """
    Vẽ các tri giác (mùi, gió, lấp lánh) tại vị trí agent.
    """
    if (
        simulation_percepts_current
        and simulation_agent_pos
        and simulation_game_status not in ["init", "error"]
    ):
        stench_val, breeze_val, glitter_val = simulation_percepts_current
        if stench_val == "?" and breeze_val == "?":
            return

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

# --- Vẽ giao diện người dùng ---
def draw_ui_elements():
    """
    Vẽ các nút điều khiển và thông tin trạng thái.
    """
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

# --- Hàm logic trò chơi ---
def initialize_simulation():
    """
    Khởi tạo mô phỏng, đọc init_data.txt và chạy Prolog.
    """
    global current_step_index, simulation_agent_pos, simulation_agent_path
    global simulation_score, simulation_time_taken, simulation_game_status
    global simulation_percepts_current, simulation_running, message_log
    global simulation_steps_data, simulation_wumpus_status, simulation_wumpus_location
    global safe_locations, maybe_wumpus_locations, no_wumpus_locations, maybe_pit_locations, no_pit_locations
    global visited_locations

    add_message("--- Khởi tạo Mô phỏng ---")
    
    # Đọc cấu hình từ init_data.txt
    if not load_init_data():
        add_message("Cảnh báo: Không thể đọc init_data.txt, sử dụng cấu hình mặc định.")
    
    # Cập nhật biến mô phỏng
    simulation_wumpus_location = list(wumpus_location_prolog)
    simulation_agent_pos = list(initial_agent_pos_prolog)
    simulation_agent_path = [list(initial_agent_pos_prolog)]
    visited_locations = [list(initial_agent_pos_prolog)]

    if not run_prolog_script():
        add_message("Khởi tạo thất bại: Không thể chạy file Prolog.")
        simulation_game_status = "error"
        simulation_steps_data = []
        message_log = [msg for msg in message_log if "ERROR" in msg or "Chào mừng" in msg]
        return

    if not load_and_parse_kb_log():
        add_message(f"Khởi tạo thất bại: Không thể phân tích '{KB_FILE_PATH}'.")
        simulation_game_status = "error"
        message_log = [msg for msg in message_log if "ERROR" in msg or "Chào mừng" in msg]
        return

    current_step_index = -1
    simulation_score = 0
    simulation_time_taken = 0
    simulation_percepts_current = None
    simulation_running = False
    simulation_game_status = "ready"
    simulation_wumpus_status = "alive"
    safe_locations.clear()
    maybe_wumpus_locations.clear()
    no_wumpus_locations.clear()
    maybe_pit_locations.clear()
    no_pit_locations.clear()

    add_message(
        f"Khởi tạo hoàn tất. Agent tại {simulation_agent_pos}. Nhấn 'Start Sim'."
    )
    message_log = message_log[-MAX_LOG_LINES:]

def handle_start_press():
    """
    Xử lý khi nhấn nút Start Sim.
    """
    global current_step_index, simulation_game_status, simulation_percepts_current
    global simulation_running, simulation_score, simulation_time_taken, last_auto_step_time
    global simulation_agent_pos, simulation_wumpus_status, simulation_wumpus_location
    global safe_locations, maybe_wumpus_locations, no_wumpus_locations, maybe_pit_locations, no_pit_locations

    if not simulation_steps_data:
        add_message("Lỗi: Không có dữ liệu mô phỏng. Không thể bắt đầu.")
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
        add_message("Lỗi: Thiếu dữ liệu tri giác cho vòng đầu tiên trong kb.txt.")
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
        f"Bước 0: Agent tại {simulation_agent_pos}. Tri giác: {initial_percepts}. Điểm: {simulation_score}, Thời gian: {simulation_time_taken}. Trạng thái: playing"
    )
    for msg in initial_messages:
        if not msg.startswith("I'm going to:"):
            add_message(msg)

    if not step_by_step_mode:
        add_message("Mô phỏng bắt đầu (Chế độ Tự động).")
        simulation_running = True
        last_auto_step_time = pygame.time.get_ticks()
    else:
        add_message("Mô phỏng bắt đầu (Chế độ Bước). Nhấn 'Next Step' để tiếp tục.")
        simulation_running = False

def advance_simulation_step():
    """
    Tiến hành bước mô phỏng tiếp theo.
    """
    global current_step_index, simulation_agent_pos, simulation_agent_path
    global simulation_score, simulation_time_taken, simulation_game_status
    global simulation_percepts_current, simulation_running
    global simulation_wumpus_status, simulation_wumpus_location
    global safe_locations, maybe_wumpus_locations, no_wumpus_locations, maybe_pit_locations, no_pit_locations

    if simulation_game_status != "playing":
        simulation_running = False
        return False

    if current_step_index + 1 >= len(simulation_steps_data):
        add_message("Đã đến cuối dữ liệu mô phỏng.")
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
            f"Lỗi: Thiếu dữ liệu quan trọng cho vòng {current_step_index}. Dừng lại."
        )
        print(f"Dữ liệu debug vòng {current_step_index}: {round_data}")
        simulation_game_status = "error"
        simulation_running = False
        return False

    add_message(
        f"Bước {current_step_index}: Agent tại {current_pos}. Tri giác: {current_percepts}. Điểm: {current_score}, Thời gian: {current_time}. Trạng thái: {current_status}"
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
        add_message(f"--- Mô phỏng {simulation_game_status.upper()} ---")
        return False

    return True

# --- Vòng lặp chính ---
async def main():
    """
    Vòng lặp chính của trò chơi, xử lý sự kiện và cập nhật giao diện.
    """
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
                    add_message("Nút Reset được nhấn.")
                    message_log = [
                        "Chào mừng đến với Wumpus World (Simulated)! Vui lòng nhấn 'Start Sim' để bắt đầu."
                    ]
                    initialize_simulation()
                elif start_btn_rect.collidepoint(mouse_pos):
                    if simulation_game_status == "ready":
                        handle_start_press()
                    elif simulation_game_status == "playing":
                        if step_by_step_mode:
                            add_message("Sử dụng nút 'Next Step' trong Chế độ Bước.")
                        elif simulation_running:
                            add_message("Nút Tạm dừng Mô phỏng được nhấn.")
                            simulation_running = False
                        else:
                            add_message("Nút Tiếp tục Mô phỏng được nhấn.")
                            simulation_running = True
                            last_auto_step_time = current_time_ms
                    else:
                        add_message("Nút Start Sim được nhấn (Đặt lại).")
                        message_log = [
                            "Chào mừng đến với Wumpus World (Simulated)! Vui lòng nhấn 'Start Sim' để bắt đầu."
                        ]
                        initialize_simulation()
                elif step_btn_rect.collidepoint(mouse_pos):
                    if step_by_step_mode and simulation_game_status == "playing":
                        add_message("Nút Next Step được nhấn.")
                        if advance_simulation_step():
                            add_message(f"Đã tiến tới bước {current_step_index}.")
                        else:
                            add_message("Không thể tiến thêm.")
                elif step_mode_btn_rect.collidepoint(mouse_pos):
                    step_by_step_mode = not step_by_step_mode
                    add_message(
                        f"Chế độ Bước được chuyển thành {'ON' if step_by_step_mode else 'OFF'}."
                    )
                    if step_by_step_mode and simulation_running:
                        simulation_running = False
                        add_message("Mô phỏng tạm dừng do Chế độ Bước BẬT.")
                    elif not step_by_step_mode and simulation_game_status == "playing":
                        simulation_running = True
                        last_auto_step_time = current_time_ms
                        add_message("Mô phỏng tiếp tục ở Chế độ Tự động.")

        if (
            simulation_running
            and not step_by_step_mode
            and simulation_game_status == "playing"
        ):
            if current_time_ms - last_auto_step_time >= auto_step_delay:
                if advance_simulation_step():
                    last_auto_step_time = current_time_ms
                else:
                    add_message("Mô phỏng dừng: Hết bước hoặc trò chơi kết thúc.")
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