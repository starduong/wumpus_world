# config_ui.py
# Giao diện cấu hình map cho game Wumpus World
import pygame
import sys
from collections import deque
import subprocess
import json

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

# Mặc định
map_size = 4
wumpus_pos = [1, 3]
pit_positions = [[3, 1], [3, 3], [4, 4]]
gold_pos = [2, 3]

input_fields = {
    "Map Size": "4",
    "Wumpus": {"X": "1", "Y": "3"},
    "Pit1": {"X": "3", "Y": "1"},
    "Pit2": {"X": "3", "Y": "3"},
    "Pit3": {"X": "4", "Y": "4"},
    "Gold": {"X": "2", "Y": "3"},
}

active_field = None  # tuple: (key, subkey)
error_message = ""
cursor_visible = True
cursor_timer = 0

screen = pygame.display.set_mode((1100, 800))
pygame.display.set_caption("Wumpus Map Config")
pygame.display.set_mode((1100, 800), pygame.SHOWN)

# Load images
agent_img = pygame.image.load("../image/agent.png")
wumpus_img = pygame.image.load("../image/wumpus.png")
pit_img = pygame.image.load("../image/pit.png")
gold_img = pygame.image.load("../image/gold.png")

def draw_map():
    pygame.draw.rect(screen, BLACK, (50, 50, CELL_SIZE * map_size, CELL_SIZE * map_size), 2)
    for row in range(map_size):
        for col in range(map_size):
            rect = pygame.Rect(50 + col * CELL_SIZE, 50 + row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, GRAY, rect, 1)
            coord_text = FONT_FAINT.render(f"({col+1},{map_size-row})", True, FAINT_GRAY)
            screen.blit(coord_text, (rect.x + 3, rect.y + 3))

    def draw_image(pos, img):
        x, y = pos
        gx, gy = x - 1, map_size - y
        px = 50 + gx * CELL_SIZE + 5
        py = 50 + gy * CELL_SIZE + 5
        scaled = pygame.transform.scale(img, (CELL_SIZE - 10, CELL_SIZE - 10))
        screen.blit(scaled, (px, py))

    draw_image([1, 1], agent_img)
    draw_image(wumpus_pos, wumpus_img)
    for p in pit_positions:
        draw_image(p, pit_img)
    draw_image(gold_pos, gold_img)

def draw_inputs():
    x0, y0 = 700, 50
    idx = 0
    for key, val in input_fields.items():
        if key == "Map Size":
            key_text = FONT.render(f"{key}:", True, BLACK)
            cursor = "|" if active_field == (key, None) and cursor_visible else ""
            val_text = FONT.render(val + cursor, True, BLACK)
            screen.blit(key_text, (x0, y0 + idx * 40))
            rect = pygame.Rect(x0 + 110, y0 + idx * 40, 50, 25)
            pygame.draw.rect(screen, RED if active_field == (key, None) else BLACK, rect, 2)
            screen.blit(val_text, (rect.x + 5, rect.y + 3))
            idx += 1
        else:
            key_text = FONT.render(f"{key}:", True, BLACK)
            screen.blit(key_text, (x0, y0 + idx * 40))
            for j, subkey in enumerate(["X", "Y"]):
                cursor = "|" if active_field == (key, subkey) and cursor_visible else ""
                val_text = FONT.render(val[subkey] + cursor, True, BLACK)
                rect = pygame.Rect(x0 + 110 + j * 60, y0 + idx * 40, 50, 25)
                pygame.draw.rect(screen, RED if active_field == (key, subkey) else BLACK, rect, 2)
                screen.blit(val_text, (rect.x + 5, rect.y + 3))
            idx += 1

def draw_error():
    if error_message:
        err_text = FONT.render(f"Lỗi: {error_message}", True, RED)
        screen.blit(err_text, (50, 20))

def validate_and_update():
    global map_size, wumpus_pos, pit_positions, gold_pos, error_message
    try:
        ms = int(input_fields["Map Size"])
        if ms < 4 or ms > MAP_MAX_SIZE:
            raise ValueError("Map size phải từ 4 đến 10")

        wp = [int(input_fields["Wumpus"]["X"]), int(input_fields["Wumpus"]["Y"])]
        g = [int(input_fields["Gold"]["X"]), int(input_fields["Gold"]["Y"])]
        pits = [
            [int(input_fields[f"Pit{i+1}"]["X"]), int(input_fields[f"Pit{i+1}"]["Y"])] for i in range(3)
        ]

        for pos in [wp, g] + pits:
            if not (1 <= pos[0] <= ms and 1 <= pos[1] <= ms):
                raise ValueError("Tọa độ ngoài phạm vi")
            if pos == [1, 1]:
                raise ValueError("Không đặt tại vị trí agent")

        if wp in [[1, 2], [2, 1]]:
            raise ValueError("Quái vật không được nằm sát agent")

        block = [tuple(wp)] + [tuple(p) for p in pits]
        visited = set()
        queue = deque([[1, 1]])
        while queue:
            cur = queue.popleft()
            if cur == g:
                map_size = ms
                wumpus_pos = wp
                pit_positions = pits
                gold_pos = g
                error_message = ""
                return True
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = cur[0]+dx, cur[1]+dy
                if 1 <= nx <= ms and 1 <= ny <= ms and (nx, ny) not in visited and (nx, ny) not in block:
                    visited.add((nx, ny))
                    queue.append([nx, ny])
        raise ValueError("Không có đường tới kho báu")
    except Exception as e:
        error_message = str(e)
        return False

def main():
    global active_field, cursor_visible, cursor_timer
    clock = pygame.time.Clock()
    running = True
    while running:
        screen.fill(WHITE)
        draw_map()
        draw_inputs()
        draw_error()

        update_btn = pygame.Rect(700, 400, 120, 40)
        play_btn = pygame.Rect(700, 460, 120, 40)
        pygame.draw.rect(screen, GREEN, update_btn)
        pygame.draw.rect(screen, RED, play_btn)
        screen.blit(FONT.render("Cập nhật", True, WHITE), (update_btn.x + 10, update_btn.y + 8))
        screen.blit(FONT.render("Chơi", True, WHITE), (play_btn.x + 30, play_btn.y + 8))

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
                if update_btn.collidepoint(event.pos):
                    validate_and_update()
                elif play_btn.collidepoint(event.pos):
                    if validate_and_update():
                        print("Khởi động game...")
                        args = [
                                "python",  
                                "wumpus_ui.py",
                                str(map_size),
                                str(wumpus_pos),  # Đây sẽ là string như "[1,3]"
                                str(pit_positions),  # Đây sẽ là string như "[[3,1],[3,3],[4,4]]"
                                str(gold_pos)  # Đây sẽ là string như "[2,3]"
                            ]
                        subprocess.Popen(args)
                        pygame.quit()
                        sys.exit()

                x0, y0 = 700, 50
                idx = 0
                for key, val in input_fields.items():
                    if key == "Map Size":
                        rect = pygame.Rect(x0 + 110, y0 + idx * 40, 50, 25)
                        if rect.collidepoint(event.pos):
                            active_field = (key, None)
                        idx += 1
                    else:
                        for j, subkey in enumerate(["X", "Y"]):
                            rect = pygame.Rect(x0 + 110 + j * 60, y0 + idx * 40, 50, 25)
                            if rect.collidepoint(event.pos):
                                active_field = (key, subkey)
                        idx += 1
            elif event.type == pygame.KEYDOWN and active_field:
                key, subkey = active_field
                if key == "Map Size":
                    if event.key == pygame.K_BACKSPACE:
                        input_fields[key] = input_fields[key][:-1]
                    elif event.key == pygame.K_RETURN:
                        active_field = None
                    elif event.unicode.isdigit():
                        input_fields[key] += event.unicode
                else:
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