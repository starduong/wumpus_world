import pygame
import sys
from collections import deque
import subprocess
import json
import os
import random

pygame.init()
FONT = pygame.font.SysFont("arial", 20)
FONT_FAINT = pygame.font.SysFont("arial", 16)

CELL_SIZE = 80
MAP_MAX_SIZE = 8

# Màu
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
GOLD_COLOR = (255, 215, 0)
FAINT_GRAY = (180, 180, 180)
BLUE = (0, 0, 255)
LIGHT_BLUE = (173, 216, 230)

# Mặc định
map_size = 4
old_map_size = map_size
wumpus_pos = [[1, 3]]
pit_positions = [[3, 1], [3, 3]]
gold_pos = [2, 3]

input_fields = {
    "Wumpus": {"X": "1", "Y": "3"},
    "Pit1": {"X": "3", "Y": "1"},
    "Pit2": {"X": "3", "Y": "3"},
    "Gold": {"X": "2", "Y": "3"},
}
invalid_fields = set()

active_field = None
error_message = ""
cursor_visible = True
cursor_timer = 0
show_dropdown = False
map_sizes = ["4", "5", "6", "7", "8"]
selected_size = "4"

screen = pygame.display.set_mode((1100, 800))
pygame.display.set_caption("Wumpus Map Config")
pygame.display.set_mode((1100, 800), pygame.SHOWN)

# Load images
agent_img = pygame.image.load("../image/agent.png")
wumpus_img = pygame.image.load("../image/wumpus.png")
pit_img = pygame.image.load("../image/pit.png")
gold_img = pygame.image.load("../image/gold.png")


def draw_map():
    pygame.draw.rect(
        screen, BLACK, (50, 50, CELL_SIZE * map_size, CELL_SIZE * map_size), 2
    )
    for row in range(map_size):
        for col in range(map_size):
            rect = pygame.Rect(
                50 + col * CELL_SIZE, 50 + row * CELL_SIZE, CELL_SIZE, CELL_SIZE
            )
            pygame.draw.rect(screen, GRAY, rect, 1)
            coord_text = FONT_FAINT.render(
                f"({col+1},{map_size-row})", True, FAINT_GRAY
            )
            screen.blit(coord_text, (rect.x + 3, rect.y + 3))

    def draw_image(pos, img):
        x, y = pos
        gx, gy = x - 1, map_size - y
        px = 50 + gx * CELL_SIZE + 5
        py = 50 + gy * CELL_SIZE + 5
        scaled = pygame.transform.scale(img, (CELL_SIZE - 10, CELL_SIZE - 10))
        screen.blit(scaled, (px, py))

    draw_image([1, 1], agent_img)
    for w in wumpus_pos:
        draw_image(w, wumpus_img)
    for p in pit_positions:
        draw_image(p, pit_img)
    draw_image(gold_pos, gold_img)


def draw_inputs():
    x0, y0 = 700, 50
    idx = 0

    # Draw other input fields first
    for key in sorted(input_fields.keys(), key=lambda x: (x.split("t")[0], x)):
        if isinstance(input_fields[key], dict):
            key_text = FONT.render(f"{key}:", True, BLACK)
            screen.blit(key_text, (x0, y0 + idx * 40))
            for j, subkey in enumerate(["X", "Y"]):
                cursor = "|" if active_field == (key, subkey) and cursor_visible else ""
                val_text = FONT.render(input_fields[key][subkey] + cursor, True, BLACK)
                rect = pygame.Rect(x0 + 110 + j * 60, y0 + idx * 40, 50, 25)
                border_color = RED if active_field == (key, subkey) else BLACK
                if key in invalid_fields:
                    border_color = RED
                pygame.draw.rect(screen, border_color, rect, 2)

                screen.blit(val_text, (rect.x + 5, rect.y + 3))
            idx += 1

    # Draw map size dropdown at the bottom
    dropdown_y = 50 + idx * 40 + 20  # Position below other inputs
    size_text = FONT.render("Map Size:", True, BLACK)
    screen.blit(size_text, (x0, dropdown_y))

    # Draw dropdown box
    dropdown_rect = pygame.Rect(x0 + 110, dropdown_y, 50, 25)
    pygame.draw.rect(screen, LIGHT_BLUE if show_dropdown else WHITE, dropdown_rect)
    pygame.draw.rect(screen, BLUE, dropdown_rect, 2)

    # Draw selected size
    selected_text = FONT.render(selected_size, True, BLACK)
    screen.blit(selected_text, (dropdown_rect.x + 5, dropdown_rect.y + 3))

    # Draw dropdown arrow
    arrow_points = [
        (dropdown_rect.right - 15, dropdown_rect.centery - 5),
        (dropdown_rect.right - 5, dropdown_rect.centery - 5),
        (dropdown_rect.right - 10, dropdown_rect.centery + 5),
    ]
    pygame.draw.polygon(screen, BLACK, arrow_points)

    # Draw dropdown options if open
    if show_dropdown:
        for i, size in enumerate(map_sizes):
            option_rect = pygame.Rect(x0 + 110, dropdown_y + 25 + i * 25, 50, 25)
            pygame.draw.rect(screen, WHITE, option_rect)
            pygame.draw.rect(screen, BLACK, option_rect, 1)
            option_text = FONT.render(size, True, BLACK)
            screen.blit(option_text, (option_rect.x + 5, option_rect.y + 3))


def get_wumpus_pit_count(size):
    return {4: (1, 2), 5: (2, 3), 6: (3, 4), 7: (4, 5), 8: (5, 6)}.get(size, (1, 2))


def is_near(pos1, pos2):
    return (abs(pos1[0] - pos2[0]) == 1 and pos1[1] == pos2[1]) or (
        abs(pos1[1] - pos2[1]) == 1 and pos1[0] == pos2[0]
    )


def is_duplicate_or_near(pos, positions):
    return any(p == pos or is_near(p, pos) for p in positions)


def euclidean_distance(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def generate_new_positions(
    count, existing, blocked, size, min_distance_from=None, min_dist=0
):
    positions = []
    while len(positions) < count:
        new_pos = [random.randint(1, size), random.randint(1, size)]
        if (
            new_pos == [1, 1]
            or new_pos == [1, 2]
            or new_pos == [2, 1]
            or new_pos == [2, 2]
            or new_pos == [1, 3]
            or new_pos == [3, 1]
        ):
            continue
        if is_duplicate_or_near(new_pos, existing + blocked + positions):
            continue
        if min_distance_from:
            if any(
                euclidean_distance(new_pos, p) < min_dist for p in min_distance_from
            ):
                continue
        positions.append(new_pos)
    return positions


def reset_map(ms):
    global map_size, input_fields, wumpus_pos, pit_positions, gold_pos

    input_fields.clear()
    map_size = ms

    req_w, req_p = get_wumpus_pit_count(ms)

    player_start = [1, 1]

    # Sinh vàng: cách người chơi đúng map_size - 1
    while True:
        g = [random.randint(1, ms), random.randint(1, ms)]
        if g != player_start and euclidean_distance(g, player_start) == ms - 1:
            gold_pos = g
            input_fields["Gold"] = {"X": str(g[0]), "Y": str(g[1])}
            break

    blocked = [player_start, gold_pos]

    # Sinh wumpus: từng con phải cách xa các con trước đó >= 2
    wumpus_pos = []
    for i in range(req_w):
        new_w = generate_new_positions(
            1, [], blocked + wumpus_pos, ms, min_distance_from=wumpus_pos, min_dist=2
        )[0]
        wumpus_pos.append(new_w)
        input_fields[f"Wumpus{i+1}"] = {"X": str(new_w[0]), "Y": str(new_w[1])}
        blocked.append(new_w)

    # Sinh pit: cũng cách xa pit khác >= 2
    pit_positions = []
    for i in range(req_p):
        new_p = generate_new_positions(
            1,
            [],
            blocked + pit_positions,
            ms,
            min_distance_from=pit_positions,
            min_dist=2,
        )[0]
        pit_positions.append(new_p)
        input_fields[f"Pit{i+1}"] = {"X": str(new_p[0]), "Y": str(new_p[1])}
        blocked.append(new_p)


def validate_and_update():
    global map_size, wumpus_pos, pit_positions, gold_pos, error_message, selected_size, invalid_fields
    try:
        invalid_fields.clear()
        ms = int(selected_size)

        # --- Lấy vị trí vàng ---
        if "Gold" not in input_fields:
            raise ValueError("Gold position missing")
        g = [int(input_fields["Gold"]["X"]), int(input_fields["Gold"]["Y"])]

        # --- Lấy wumpus ---
        valid_wumpus = []
        for k in input_fields:
            if k.startswith("Wumpus"):
                pos = [int(input_fields[k]["X"]), int(input_fields[k]["Y"])]
                valid_wumpus.append(pos)

        # --- Lấy pit ---
        valid_pits = []
        for k in input_fields:
            if k.startswith("Pit"):
                pos = [int(input_fields[k]["X"]), int(input_fields[k]["Y"])]
                valid_pits.append(pos)

        # --- Kiểm tra trùng ---
        all_pos = valid_wumpus + valid_pits + [g]
        if len(all_pos) != len(set(tuple(p) for p in all_pos)):
            raise ValueError("Duplicate location between monster, pit or treasure")

        # --- Gán lại ---
        wumpus_pos = valid_wumpus
        pit_positions = valid_pits
        gold_pos = g
        map_size = ms
        error_message = ""
        return True

    except Exception as e:
        error_message = str(e)
        return False


def draw_error():
    if error_message:
        err_text = FONT.render(f"ERROR: {error_message}", True, RED)
        screen.blit(err_text, (50, 20))


def main():
    global active_field, cursor_visible, cursor_timer, show_dropdown, selected_size, map_size
    clock = pygame.time.Clock()
    running = True
    while running:
        screen.fill(WHITE)
        draw_map()
        draw_inputs()
        draw_error()

        # Move buttons to left side below the map
        buttons_y = 50 + CELL_SIZE * map_size + 20
        update_btn = pygame.Rect(50, buttons_y, 120, 40)
        play_btn = pygame.Rect(200, buttons_y, 120, 40)
        pygame.draw.rect(screen, GREEN, update_btn)
        pygame.draw.rect(screen, RED, play_btn)
        screen.blit(
            FONT.render("UPDATE", True, BLACK), (update_btn.x + 10, update_btn.y + 8)
        )
        screen.blit(FONT.render("PLAY", True, BLACK), (play_btn.x + 30, play_btn.y + 8))

        pygame.display.flip()

        cursor_timer += clock.get_time()
        if cursor_timer >= 500:
            cursor_visible = not cursor_visible
            cursor_timer = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x0, y0 = 700, 50

                # Check if clicked on map size dropdown
                # Calculate dropdown position based on number of input fields
                num_fields = len(input_fields)
                dropdown_y = 50 + num_fields * 40 + 20
                dropdown_rect = pygame.Rect(x0 + 110, dropdown_y, 50, 25)

                if dropdown_rect.collidepoint(event.pos):
                    show_dropdown = not show_dropdown
                elif show_dropdown:
                    # Check if clicked on a dropdown option
                    for i, size in enumerate(map_sizes):
                        option_rect = pygame.Rect(
                            x0 + 110, dropdown_y + 25 + i * 25, 50, 25
                        )
                        if option_rect.collidepoint(event.pos):
                            selected_size = size
                            show_dropdown = False
                            ms = int(size)
                            reset_map(ms)
                            break

                    else:
                        show_dropdown = False
                else:
                    show_dropdown = False

                # Check buttons
                if update_btn.collidepoint(event.pos):
                    validate_and_update()
                elif play_btn.collidepoint(event.pos):
                    if validate_and_update():
                        init_data_path = os.path.join(
                            os.path.dirname(__file__), "init_data.txt"
                        )
                        with open(init_data_path, "w", encoding="utf-8") as f:
                            f.write(f"{map_size}.\n")
                            f.write(f"{wumpus_pos}.\n")
                            f.write(f"{pit_positions}.\n")
                            f.write(f"{gold_pos}.\n")
                        args = [
                            "python",
                            os.path.join(os.path.dirname(__file__), "wumpus_ui.py"),
                            str(map_size),
                            str(wumpus_pos),
                            str(pit_positions),
                            str(gold_pos),
                        ]
                        subprocess.Popen(args)
                        pygame.quit()
                        sys.exit()

                # Check other input fields
                idx = 0
                for key in sorted(
                    input_fields.keys(), key=lambda x: (x.split("t")[0], x)
                ):
                    if isinstance(input_fields[key], dict):
                        for j, subkey in enumerate(["X", "Y"]):
                            rect = pygame.Rect(x0 + 110 + j * 60, y0 + idx * 40, 50, 25)
                            if rect.collidepoint(event.pos):
                                active_field = (key, subkey)
                        idx += 1
            elif event.type == pygame.KEYDOWN and active_field:
                key, subkey = active_field
                if event.key == pygame.K_BACKSPACE:
                    input_fields[key][subkey] = input_fields[key][subkey][:-1]
                elif event.key == pygame.K_RETURN:
                    active_field = None
                elif event.unicode.isdigit():
                    input_fields[key][subkey] += event.unicode

        clock.tick(30)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
