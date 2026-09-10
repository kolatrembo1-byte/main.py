import pygame
import random
import sys
import math
import array
import json
import os

# Инициализация аудио и графики
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

if hasattr(pygame.key, "stop_text_input"):
    pygame.key.stop_text_input()

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("SNAKEHUNT")
clock = pygame.time.Clock()

# --- ФАЙЛ СОХРАНЕНИЙ (JSON) ---
SAVE_FILE = "snakehunt_save.json"

def load_save():
    default_data = {"unlocked_level": 1, "endless_record": 0}
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("unlocked_level", 1), data.get("endless_record", 0)
        except Exception:
            return default_data["unlocked_level"], default_data["endless_record"]
    return default_data["unlocked_level"], default_data["endless_record"]

def write_save(unlocked_lvl, record):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump({"unlocked_level": unlocked_lvl, "endless_record": record}, f)
    except Exception:
        pass

unlocked_level, endless_record = load_save()

# --- Безопасная адаптивная сетка ---
HEADER_HEIGHT = int(HEIGHT * 0.08)
MARGIN_SIDE = int(WIDTH * 0.05)
MARGIN_BOTTOM = int(HEIGHT * 0.10)
WALL_THICKNESS = 4

PLAY_AREA_W = WIDTH - 2 * MARGIN_SIDE
PLAY_AREA_H = HEIGHT - HEADER_HEIGHT - MARGIN_BOTTOM

BLOCK_SIZE = max(24, min(PLAY_AREA_W // 14, PLAY_AREA_H // 20))
GRID_X = PLAY_AREA_W // BLOCK_SIZE
GRID_Y = PLAY_AREA_H // BLOCK_SIZE

OFFSET_X = MARGIN_SIDE + (PLAY_AREA_W - (GRID_X * BLOCK_SIZE)) // 2
OFFSET_Y = HEADER_HEIGHT + (PLAY_AREA_H - (GRID_Y * BLOCK_SIZE)) // 2

ARENA_RECT = pygame.Rect(OFFSET_X, OFFSET_Y, GRID_X * BLOCK_SIZE, GRID_Y * BLOCK_SIZE)

# Цветовая палитра
CLR_BG = (9, 12, 20)
CLR_ARENA_BG = (12, 16, 26)
CLR_GRID = (19, 25, 40)
CLR_BORDER = (45, 60, 88)
CLR_BORDER_GLOW = (56, 189, 248)
CLR_HEADER = (13, 17, 28)
CLR_TEXT = (243, 246, 252)
CLR_MUTED = (110, 128, 153)
CLR_ACCENT = (56, 189, 248)
CLR_GOLD = (251, 191, 36)
CLR_FREEZE = (56, 189, 248)
CLR_CARD = (18, 24, 39)
CLR_CARD_BORDER = (38, 50, 75)
CLR_BTN = (24, 32, 52)

f_title = pygame.font.SysFont(None, int(WIDTH * 0.095))
f_sub = pygame.font.SysFont(None, int(WIDTH * 0.034))
f_ui = pygame.font.SysFont(None, int(WIDTH * 0.044))
f_card = pygame.font.SysFont(None, int(WIDTH * 0.052))

# Запечённый фон
background_surface = pygame.Surface((WIDTH, HEIGHT)).convert()
background_surface.fill(CLR_BG)
pygame.draw.rect(background_surface, CLR_ARENA_BG, ARENA_RECT)

for x in range(OFFSET_X, OFFSET_X + GRID_X * BLOCK_SIZE + 1, BLOCK_SIZE):
    pygame.draw.line(background_surface, CLR_GRID, (x, OFFSET_Y), (x, OFFSET_Y + GRID_Y * BLOCK_SIZE), 1)
for y in range(OFFSET_Y, OFFSET_Y + GRID_Y * BLOCK_SIZE + 1, BLOCK_SIZE):
    pygame.draw.line(background_surface, CLR_GRID, (OFFSET_X, y), (OFFSET_X + GRID_X * BLOCK_SIZE, y), 1)

pygame.draw.rect(background_surface, CLR_BORDER, ARENA_RECT.inflate(WALL_THICKNESS * 2, WALL_THICKNESS * 2), width=WALL_THICKNESS, border_radius=8)
pygame.draw.rect(background_surface, CLR_BORDER_GLOW, ARENA_RECT.inflate(2, 2), width=1, border_radius=6)

# --- Генератор процедурной музыки и звуков ---
def generate_sine_wave(freq, duration, volume=0.5):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    buf = array.array("h")
    for i in range(num_samples):
        t = i / sample_rate
        val = int(math.sin(2 * math.pi * freq * t) * 32767 * volume)
        buf.append(val)
        buf.append(val)
    return pygame.mixer.Sound(buf)

snd_eat = generate_sine_wave(587.33, 0.08, 0.4)
snd_bonus = generate_sine_wave(880.0, 0.12, 0.5)
snd_crash = generate_sine_wave(110.0, 0.25, 0.6)
snd_win = generate_sine_wave(659.25, 0.2, 0.4)

melody_notes = [
    (146.83, 0.2), (146.83, 0.2), (220.0, 0.2), (196.0, 0.2),
    (174.61, 0.2), (164.81, 0.2), (146.83, 0.2), (220.0, 0.2),
    (130.81, 0.2), (130.81, 0.2), (196.0, 0.2), (174.61, 0.2),
    (164.81, 0.2), (146.83, 0.2), (130.81, 0.2), (164.81, 0.2)
]
melody_sounds = [generate_sine_wave(f, d, 0.3) for f, d in melody_notes]

music_volume = 0.5
music_channel = pygame.mixer.Channel(0)
sfx_channel = pygame.mixer.Channel(1)

current_note_idx = 0
last_note_time = pygame.time.get_ticks()

def update_music(now):
    global current_note_idx, last_note_time
    if music_volume > 0 and (now - last_note_time >= 220):
        snd = melody_sounds[current_note_idx]
        snd.set_volume(music_volume)
        music_channel.play(snd)
        current_note_idx = (current_note_idx + 1) % len(melody_sounds)
        last_note_time = now

def play_sfx(sound):
    if music_volume > 0:
        sound.set_volume(min(1.0, music_volume * 1.2))
        sfx_channel.play(sound)

LEVELS = {
    1:  {"speed": 130, "target": 6,  "name": "Зелёная зона"},
    2:  {"speed": 122, "target": 7,  "name": "Обелиски"},
    3:  {"speed": 114, "target": 8,  "name": "Бастион"},
    4:  {"speed": 106, "target": 9,  "name": "Крестовина"},
    5:  {"speed": 98,  "target": 10, "name": "Шкатулка"},
    6:  {"speed": 90,  "target": 11, "name": "Змейка"},
    7:  {"speed": 82,  "target": 12, "name": "Шлюзы"},
    8:  {"speed": 74,  "target": 14, "name": "Пилоны"},
    9:  {"speed": 66,  "target": 15, "name": "Цитадель"},
    10: {"speed": 58,  "target": 18, "name": "Инферно"}
}

def generate_level_walls(lvl):
    walls = {}
    mx, my = GRID_X // 2, GRID_Y // 2

    if lvl == 2:
        for dx in (-3, 3):
            for dy in (-3, 3):
                walls[(mx + dx, my + dy)] = "SPIKE"
    elif lvl == 3:
        for x in range(2, GRID_X - 2):
            if abs(x - mx) > 1:
                walls[(x, my - 3)] = "HAZARD" if x % 2 == 0 else "RUNE"
                walls[(x, my + 3)] = "HAZARD" if x % 2 == 0 else "RUNE"
    elif lvl == 4:
        for i in range(2, 5):
            walls[(mx - i, my - i)] = "CRYSTAL"
            walls[(mx + i, my - i)] = "CRYSTAL"
            walls[(mx - i, my + i)] = "CRYSTAL"
            walls[(mx + i, my + i)] = "CRYSTAL"
    elif lvl == 5:
        for x in range(mx - 3, mx + 4):
            walls[(x, my - 4)] = "RUNE"
            walls[(x, my + 4)] = "RUNE"
        for y in range(my - 4, my + 5):
            if abs(y - my) > 1:
                walls[(mx - 4, y)] = "HAZARD"
                walls[(mx + 4, y)] = "HAZARD"
    elif lvl == 6:
        for x in range(2, GRID_X - 4): walls[(x, my - 4)] = "CRYSTAL"
        for x in range(4, GRID_X - 2): walls[(x, my)] = "SPIKE"
        for x in range(2, GRID_X - 4): walls[(x, my + 4)] = "CRYSTAL"
    elif lvl == 7:
        for y in range(2, GRID_Y - 2):
            if y not in (my, my - 1, my + 1):
                walls[(mx - 2, y)] = "HAZARD"
                walls[(mx + 2, y)] = "RUNE"
    elif lvl == 8:
        for gx in range(2, GRID_X - 2, 3):
            for gy in range(2, GRID_Y - 2, 3):
                walls[(gx, gy)] = "SPIKE" if (gx + gy) % 2 == 0 else "CRYSTAL"
    elif lvl == 9:
        for x in range(2, GRID_X - 2):
            walls[(x, 2)] = "HAZARD"
            walls[(x, GRID_Y - 3)] = "HAZARD"
        for y in range(2, GRID_Y - 2):
            if y not in (my, my - 1):
                walls[(2, y)] = "RUNE"
                walls[(GRID_X - 3, y)] = "RUNE"
    elif lvl == 10:
        for i in range(2, GRID_X - 2, 3):
            for y in range(2, GRID_Y - 2):
                t = "CRYSTAL" if y % 2 == 0 else "HAZARD"
                if (i // 3) % 2 == 0 and y > 4: walls[(i, y)] = t
                elif (i // 3) % 2 != 0 and y < GRID_Y - 5: walls[(i, y)] = t
    return walls

def get_free_cell(snake, walls, other_items=()):
    occupied = set(snake) | set(walls.keys()) | set(other_items)
    while True:
        pos = (random.randint(0, GRID_X - 1), random.randint(0, GRID_Y - 1))
        if pos not in occupied:
            return pos

bonus_item = None
freeze_end_time = 0
game_mode = "CAMPAIGN"
current_level = 1

def start_game(mode="CAMPAIGN", lvl=1):
    global bonus_item, freeze_end_time, game_mode
    game_mode = mode
    mx, my = GRID_X // 2, GRID_Y // 2
    snake = [(mx, my), (mx - 1, my), (mx - 2, my)]
    
    if mode == "CAMPAIGN":
        walls = generate_level_walls(lvl)
    else:
        walls = {}

    while any(s in walls for s in snake):
        snake = [(s[0], s[1] + 1) for s in snake]
        
    food = get_free_cell(snake, walls)
    bonus_item = None
    freeze_end_time = 0
    prev_snake = list(snake)
    return snake, prev_snake, (1, 0), (1, 0), food, walls, 0

snake, prev_snake, direction, next_direction, food, walls, apples_eaten = start_game("CAMPAIGN", current_level)

state = "MENU"
touch_start = None
last_step = pygame.time.get_ticks()
last_bonus_attempt = pygame.time.get_ticks()

# Геометрия меню
btn_w, btn_h = int(WIDTH * 0.74), int(HEIGHT * 0.068)
play_rect = pygame.Rect((WIDTH - btn_w) // 2, int(HEIGHT * 0.42), btn_w, btn_h)
endless_rect = pygame.Rect((WIDTH - btn_w) // 2, int(HEIGHT * 0.505), btn_w, btn_h)
lvl_btn_rect = pygame.Rect((WIDTH - btn_w) // 2, int(HEIGHT * 0.59), btn_w, btn_h)
settings_btn_rect = pygame.Rect((WIDTH - btn_w) // 2, int(HEIGHT * 0.675), btn_w, btn_h)

# Кнопки настроек
vol_minus_rect = pygame.Rect(int(WIDTH * 0.22), int(HEIGHT * 0.44), int(WIDTH * 0.16), int(HEIGHT * 0.07))
vol_plus_rect = pygame.Rect(int(WIDTH * 0.62), int(HEIGHT * 0.44), int(WIDTH * 0.16), int(HEIGHT * 0.07))
back_settings_rect = pygame.Rect((WIDTH - btn_w) // 2, int(HEIGHT * 0.62), btn_w, btn_h)

# Кнопки экрана победы
win_card_w, win_card_h = int(WIDTH * 0.85), int(HEIGHT * 0.36)
win_card_rect = pygame.Rect((WIDTH - win_card_w) // 2, (HEIGHT - win_card_h) // 2, win_card_w, win_card_h)
win_next_btn = pygame.Rect(win_card_rect.x + int(win_card_w * 0.1), win_card_rect.y + int(win_card_h * 0.48), int(win_card_w * 0.8), int(HEIGHT * 0.065))
win_menu_btn = pygame.Rect(win_card_rect.x + int(win_card_w * 0.1), win_card_rect.y + int(win_card_h * 0.72), int(win_card_w * 0.8), int(HEIGHT * 0.065))

# Кнопки экрана проигрыша
lose_card_w, lose_card_h = int(WIDTH * 0.85), int(HEIGHT * 0.36)
lose_card_rect = pygame.Rect((WIDTH - lose_card_w) // 2, (HEIGHT - lose_card_h) // 2, lose_card_w, lose_card_h)
lose_restart_btn = pygame.Rect(lose_card_rect.x + int(lose_card_w * 0.1), lose_card_rect.y + int(lose_card_h * 0.48), int(lose_card_w * 0.8), int(HEIGHT * 0.065))
lose_menu_btn = pygame.Rect(lose_card_rect.x + int(lose_card_w * 0.1), lose_card_rect.y + int(lose_card_h * 0.72), int(lose_card_w * 0.8), int(HEIGHT * 0.065))

def draw_wall_block(surface, gx, gy, b_type):
    x = OFFSET_X + gx * BLOCK_SIZE
    y = OFFSET_Y + gy * BLOCK_SIZE
    s = BLOCK_SIZE
    cx, cy = x + s / 2, y + s / 2
    if b_type == "CRYSTAL":
        m = s * 0.2
        pygame.draw.polygon(surface, (96, 165, 250), [(x, y), (x + s, y), (cx, cy - m)])
        pygame.draw.polygon(surface, (59, 130, 246), [(x, y), (cx, cy - m), (x, y + s)])
        pygame.draw.polygon(surface, (37, 99, 235), [(x + s, y), (x + s, y + s), (cx, cy - m)])
        pygame.draw.polygon(surface, (29, 78, 216), [(x, y + s), (x + s, y + s), (cx, cy - m)])
    elif b_type == "SPIKE":
        pygame.draw.polygon(surface, (248, 113, 113), [(cx, y + 2), (x + s - 2, cy), (cx, cy)])
        pygame.draw.polygon(surface, (239, 68, 68), [(cx, y + 2), (cx, cy), (x + 2, cy)])
        pygame.draw.polygon(surface, (220, 38, 38), [(x + 2, cy), (cx, cy), (cx, y + s - 2)])
        pygame.draw.polygon(surface, (185, 28, 28), [(x + s - 2, cy), (cx, y + s - 2), (cx, cy)])
    elif b_type == "HAZARD":
        m = s * 0.22
        pygame.draw.polygon(surface, (250, 204, 21), [(x, y), (x + s, y), (x + s - m, y + m), (x + m, y + m)])
        pygame.draw.polygon(surface, (30, 35, 45), [(x, y), (x + m, y + m), (x + m, y + s - m), (x, y + s)])
        pygame.draw.polygon(surface, (234, 179, 8), [(x + s, y), (x + s, y + s), (x + s - m, y + s - m), (x + s - m, y + m)])
        pygame.draw.polygon(surface, (20, 24, 33), [(x, y + s), (x + m, y + s - m), (x + s - m, y + s - m), (x + s, y + s)])
        pygame.draw.rect(surface, (202, 138, 4), (x + m, y + m, s - 2 * m, s - 2 * m))
    else:
        m = s * 0.25
        pygame.draw.polygon(surface, (100, 116, 139), [(x, y), (x + s, y), (x + s - m, y + m), (x + m, y + m)])
        pygame.draw.polygon(surface, (71, 85, 105), [(x, y), (x + m, y + m), (x + m, y + s - m), (x, y + s)])
        pygame.draw.polygon(surface, (51, 65, 85), [(x + s, y), (x + s, y + s), (x + s - m, y + s - m), (x + s - m, y + m)])
        pygame.draw.polygon(surface, (30, 41, 59), [(x, y + s), (x + m, y + s - m), (x + s - m, y + s - m), (x + s, y + s)])
        pygame.draw.rect(surface, (148, 163, 184), (x + m, y + m, s - 2 * m, s - 2 * m))

def draw_polygon_apple(surface, gx, gy, is_gold=False):
    cx = OFFSET_X + gx * BLOCK_SIZE + BLOCK_SIZE // 2
    cy = OFFSET_Y + gy * BLOCK_SIZE + BLOCK_SIZE // 2
    r = BLOCK_SIZE * (0.48 if is_gold else 0.44)
    pts = [
        (cx, cy - r * 0.75), (cx + r * 0.7, cy - r), (cx + r, cy - r * 0.2),
        (cx + r * 0.8, cy + r * 0.8), (cx + r * 0.25, cy + r), (cx, cy + r * 0.8),
        (cx - r * 0.25, cy + r), (cx - r * 0.8, cy + r * 0.8), (cx - r, cy - r * 0.2),
        (cx - r * 0.7, cy - r)
    ]
    center_pt = (cx, cy + r * 0.1)
    if is_gold:
        facet_colors = [(254, 240, 138), (250, 204, 21), (234, 179, 8), (202, 138, 4), (161, 98, 7), (133, 77, 14), (161, 98, 7), (202, 138, 4), (250, 204, 21), (254, 249, 195)]
    else:
        facet_colors = [(255, 115, 135), (255, 75, 100), (230, 40, 75), (195, 20, 55), (170, 15, 45), (160, 10, 40), (185, 20, 50), (225, 45, 80), (255, 90, 115), (255, 140, 155)]
    for i in range(len(pts)):
        pygame.draw.polygon(surface, facet_colors[i], [center_pt, pts[i], pts[(i + 1) % len(pts)]])
    stem_c = (253, 224, 71) if is_gold else (120, 75, 40)
    leaf_c = (255, 255, 255) if is_gold else (74, 222, 128)
    pygame.draw.polygon(surface, stem_c, [(cx - 1, cy - r * 0.7), (cx + 3, cy - r * 1.3), (cx + 1, cy - r * 1.3), (cx - 2, cy - r * 0.7)])
    pygame.draw.polygon(surface, leaf_c, [(cx + 2, cy - r * 1.1), (cx + r * 0.7, cy - r * 1.4), (cx + r * 0.8, cy - r * 0.9), (cx + 2, cy - r * 0.95)])

def draw_polygon_crystal(surface, gx, gy, c_type, anim_tick):
    cx = OFFSET_X + gx * BLOCK_SIZE + BLOCK_SIZE // 2
    cy = OFFSET_Y + gy * BLOCK_SIZE + BLOCK_SIZE // 2
    r = BLOCK_SIZE * 0.44
    rot = math.sin(anim_tick * 0.005) * 0.3
    cos_a, sin_a = math.cos(rot), math.sin(rot)
    def r_pt(lx, ly): return (cx + lx * cos_a - ly * sin_a, cy + lx * sin_a + ly * cos_a)
    top, bottom = r_pt(0, -r * 1.1), r_pt(0, r * 1.1)
    left, right = r_pt(-r * 0.85, 0), r_pt(r * 0.85, 0)
    center = r_pt(0, -r * 0.1)
    if c_type == "FREEZE":
        pygame.draw.polygon(surface, (224, 242, 254), [top, right, center])
        pygame.draw.polygon(surface, (125, 211, 252), [top, center, left])
        pygame.draw.polygon(surface, (56, 189, 248), [left, center, bottom])
        pygame.draw.polygon(surface, (14, 165, 233), [right, bottom, center])
    else:
        pygame.draw.polygon(surface, (243, 232, 255), [top, right, center])
        pygame.draw.polygon(surface, (216, 180, 254), [top, center, left])
        pygame.draw.polygon(surface, (168, 85, 247), [left, center, bottom])
        pygame.draw.polygon(surface, (126, 34, 206), [right, bottom, center])

def draw_smooth_continuous_snake(surface, snake, prev_snake, direction, progress, is_frozen=False):
    pts = []
    for i in range(len(snake)):
        curr_g = snake[i]
        prev_g = prev_snake[i] if i < len(prev_snake) else curr_g
        interp_x = prev_g[0] + (curr_g[0] - prev_g[0]) * progress
        interp_y = prev_g[1] + (curr_g[1] - prev_g[1]) * progress
        pts.append((OFFSET_X + interp_x * BLOCK_SIZE + BLOCK_SIZE / 2,
                    OFFSET_Y + interp_y * BLOCK_SIZE + BLOCK_SIZE / 2))
    if len(pts) < 2: return
    base_w = BLOCK_SIZE * 0.44
    for i in range(len(pts) - 1):
        p1, p2 = pts[i], pts[i + 1]
        dx, dy = p1[0] - p2[0], p1[1] - p2[1]
        dist = math.hypot(dx, dy)
        if dist == 0: continue
        nx, ny = -dy / dist, dx / dist
        w1, w2 = base_w * (1.0 - (i / len(pts)) * 0.55), base_w * (1.0 - ((i + 1) / len(pts)) * 0.55)
        left1, right1 = (p1[0] + nx * w1, p1[1] + ny * w1), (p1[0] - nx * w1, p1[1] - ny * w1)
        left2, right2 = (p2[0] + nx * w2, p2[1] + ny * w2), (p2[0] - nx * w2, p2[1] - ny * w2)
        mid1, mid2 = (p1[0], p1[1]), (p2[0], p2[1])
        if is_frozen:
            c_left = (125, 211, 252) if i % 2 == 0 else (56, 189, 248)
            c_right = (14, 165, 233) if i % 2 == 0 else (2, 132, 199)
        else:
            c_left = (46, 215, 140) if i % 2 == 0 else (36, 195, 125)
            c_right = (30, 175, 110) if i % 2 == 0 else (24, 150, 95)
        pygame.draw.polygon(surface, c_left, [left1, mid1, mid2, left2])
        pygame.draw.polygon(surface, c_right, [mid1, right1, right2, mid2])

    p_last, p_prev = pts[-1], pts[-2]
    dx_t, dy_t = p_last[0] - p_prev[0], p_last[1] - p_prev[1]
    dist_t = math.hypot(dx_t, dy_t)
    if dist_t > 0:
        nx_t, ny_t = -dy_t / dist_t, dx_t / dist_t
        w_end = base_w * 0.45
        tip = (p_last[0] + (dx_t / dist_t) * w_end, p_last[1] + (dy_t / dist_t) * w_end)
        tail_c = (2, 132, 199) if is_frozen else (20, 130, 80)
        pygame.draw.polygon(surface, tail_c, [(p_last[0] + nx_t * w_end, p_last[1] + ny_t * w_end), tip, (p_last[0] - nx_t * w_end, p_last[1] - ny_t * w_end)])

    head_pos = pts[0]
    angle = math.atan2(direction[1], direction[0])
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    def rot(lx, ly): return (head_pos[0] + lx * cos_a - ly * sin_a, head_pos[1] + lx * sin_a + ly * cos_a)
    s = base_w
    tongue_anim = math.sin(progress * math.pi)
    t_len = s * (1.1 + 0.8 * tongue_anim)
    t_base = rot(s * 0.95, 0)
    t_fork1, t_fork2 = rot(t_base[0] - head_pos[0] + t_len, -s * 0.4), rot(t_base[0] - head_pos[0] + t_len, s * 0.4)
    t_mid = rot(t_base[0] - head_pos[0] + t_len * 0.65, 0)
    t_col = (56, 189, 248) if is_frozen else (239, 68, 68)
    pygame.draw.polygon(surface, t_col, [t_base, t_mid, t_fork1])
    pygame.draw.polygon(surface, t_col, [t_base, t_mid, t_fork2])

    p_nose = rot(s * 1.15, 0)
    p_cheek_r, p_cheek_l = rot(s * 0.35, s * 0.95), rot(s * 0.35, -s * 0.95)
    p_back_r, p_back_l = rot(-s * 0.8, s * 0.85), rot(-s * 0.8, -s * 0.85)
    p_crown = rot(-s * 0.1, 0)
    if is_frozen:
        pygame.draw.polygon(surface, (186, 230, 253), [p_nose, p_cheek_l, p_crown])
        pygame.draw.polygon(surface, (125, 211, 252), [p_nose, p_crown, p_cheek_r])
        pygame.draw.polygon(surface, (56, 189, 248), [p_crown, p_cheek_l, p_back_l])
        pygame.draw.polygon(surface, (14, 165, 233), [p_crown, p_back_r, p_cheek_r])
    else:
        pygame.draw.polygon(surface, (52, 235, 160), [p_nose, p_cheek_l, p_crown])
        pygame.draw.polygon(surface, (38, 205, 135), [p_nose, p_crown, p_cheek_r])
        pygame.draw.polygon(surface, (30, 180, 115), [p_crown, p_cheek_l, p_back_l])
        pygame.draw.polygon(surface, (25, 155, 100), [p_crown, p_back_r, p_cheek_r])

    for eye_sign in (-1, 1):
        ec = rot(s * 0.28, eye_sign * s * 0.58)
        eye_pts = [
            (ec[0] + rot(s * 0.26, 0)[0] - head_pos[0], ec[1] + rot(s * 0.26, 0)[1] - head_pos[1]),
            (ec[0] + rot(0, s * 0.2)[0] - head_pos[0], ec[1] + rot(0, s * 0.2)[1] - head_pos[1]),
            (ec[0] + rot(-s * 0.26, 0)[0] - head_pos[0], ec[1] + rot(-s * 0.26, 0)[1] - head_pos[1]),
            (ec[0] + rot(0, -s * 0.2)[0] - head_pos[0], ec[1] + rot(0, -s * 0.2)[1] - head_pos[1]),
        ]
        pygame.draw.polygon(surface, (15, 23, 42), eye_pts)
        pupil = rot(s * 0.32, eye_sign * s * 0.58)
        pygame.draw.circle(surface, (255, 255, 255), (int(pupil[0]), int(pupil[1])), max(1, int(s * 0.1)))

# --- Главный игровой цикл ---
while True:
    now = pygame.time.get_ticks()
    update_music(now)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            write_save(unlocked_level, endless_record)
            pygame.quit()
            sys.exit()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            touch_start = event.pos

            if state == "MENU":
                if play_rect.collidepoint(event.pos):
                    snake, prev_snake, direction, next_direction, food, walls, apples_eaten = start_game("CAMPAIGN", current_level)
                    state = "PLAY"
                    last_step = now
                elif endless_rect.collidepoint(event.pos):
                    snake, prev_snake, direction, next_direction, food, walls, apples_eaten = start_game("ENDLESS")
                    state = "PLAY"
                    last_step = now
                elif lvl_btn_rect.collidepoint(event.pos):
                    state = "LEVEL_SELECT"
                elif settings_btn_rect.collidepoint(event.pos):
                    state = "SETTINGS"

            elif state == "SETTINGS":
                if vol_minus_rect.collidepoint(event.pos):
                    music_volume = max(0.0, round(music_volume - 0.1, 1))
                elif vol_plus_rect.collidepoint(event.pos):
                    music_volume = min(1.0, round(music_volume + 0.1, 1))
                elif back_settings_rect.collidepoint(event.pos):
                    state = "MENU"

            elif state == "LEVEL_SELECT":
                cols, bw, bh = 2, int(WIDTH * 0.40), int(HEIGHT * 0.07)
                gap_x, gap_y = int(WIDTH * 0.05), int(HEIGHT * 0.016)
                start_y = int(HEIGHT * 0.18)
                for i in range(1, 11):
                    c, r = (i - 1) % cols, (i - 1) // cols
                    rect = pygame.Rect(int(WIDTH * 0.075) + c * (bw + gap_x), start_y + r * (bh + gap_y), bw, bh)
                    if rect.collidepoint(event.pos) and i <= unlocked_level:
                        current_level = i
                        snake, prev_snake, direction, next_direction, food, walls, apples_eaten = start_game("CAMPAIGN", current_level)
                        state = "PLAY"
                        last_step = now
                        break

            elif state == "WIN":
                if win_next_btn.collidepoint(event.pos):
                    if current_level < 10:
                        current_level += 1
                    snake, prev_snake, direction, next_direction, food, walls, apples_eaten = start_game("CAMPAIGN", current_level)
                    state = "PLAY"
                    last_step = now
                elif win_menu_btn.collidepoint(event.pos):
                    state = "MENU"

            elif state == "LOSE":
                if lose_restart_btn.collidepoint(event.pos):
                    snake, prev_snake, direction, next_direction, food, walls, apples_eaten = start_game(game_mode, current_level)
                    state = "PLAY"
                    last_step = now
                elif lose_menu_btn.collidepoint(event.pos):
                    state = "MENU"

        elif event.type == pygame.MOUSEBUTTONUP and touch_start:
            if state == "PLAY":
                dx, dy = event.pos[0] - touch_start[0], event.pos[1] - touch_start[1]
                if max(abs(dx), abs(dy)) > 20:
                    if abs(dx) > abs(dy):
                        if dx > 0 and direction != (-1, 0): next_direction = (1, 0)
                        elif dx < 0 and direction != (1, 0): next_direction = (-1, 0)
                    else:
                        if dy > 0 and direction != (0, -1): next_direction = (0, 1)
                        elif dy < 0 and direction != (0, 1): next_direction = (0, -1)
            touch_start = None

    if state == "PLAY":
        if bonus_item:
            if now - bonus_item["spawn_time"] > 8000:
                bonus_item = None
        else:
            if now - last_bonus_attempt > 6000:
                last_bonus_attempt = now
                if random.random() < 0.35:
                    b_type = random.choice(["GOLD", "FREEZE", "CUT"])
                    b_pos = get_free_cell(snake, walls, (food,))
                    bonus_item = {"pos": b_pos, "type": b_type, "spawn_time": now}

    if game_mode == "CAMPAIGN":
        base_speed = LEVELS[current_level]["speed"]
    else:
        base_speed = max(45, 125 - (apples_eaten // 2) * 3)

    is_frozen = now < freeze_end_time
    cur_speed = int(base_speed * 1.8) if is_frozen else base_speed

    if state == "PLAY" and (now - last_step >= cur_speed):
        direction = next_direction
        head = (snake[0][0] + direction[0], snake[0][1] + direction[1])

        if (head[0] < 0 or head[0] >= GRID_X or
            head[1] < 0 or head[1] >= GRID_Y or
            head in snake or head in walls):
            play_sfx(snd_crash)
            if game_mode == "ENDLESS" and apples_eaten > endless_record:
                endless_record = apples_eaten
                write_save(unlocked_level, endless_record)
            state = "LOSE"
        else:
            prev_snake = list(snake)
            snake.insert(0, head)

            if bonus_item and head == bonus_item["pos"]:
                play_sfx(snd_bonus)
                if bonus_item["type"] == "GOLD":
                    apples_eaten += 3
                    if game_mode == "ENDLESS" and apples_eaten > endless_record:
                        endless_record = apples_eaten
                        write_save(unlocked_level, endless_record)
                elif bonus_item["type"] == "FREEZE":
                    freeze_end_time = now + 5000
                elif bonus_item["type"] == "CUT":
                    cut_count = max(1, len(snake) // 3)
                    for _ in range(cut_count):
                        if len(snake) > 3:
                            snake.pop()
                            if len(prev_snake) > 3: prev_snake.pop()
                bonus_item = None

            if head == food:
                play_sfx(snd_eat)
                apples_eaten += 1
                if game_mode == "ENDLESS" and apples_eaten > endless_record:
                    endless_record = apples_eaten
                    write_save(unlocked_level, endless_record)

                if game_mode == "CAMPAIGN" and apples_eaten >= LEVELS[current_level]["target"]:
                    play_sfx(snd_win)
                    if current_level < 10:
                        unlocked_level = max(unlocked_level, current_level + 1)
                        write_save(unlocked_level, endless_record)
                    state = "WIN"
                else:
                    food = get_free_cell(snake, walls, (bonus_item["pos"],) if bonus_item else ())
            else:
                snake.pop()

        last_step = now

    # --- Отрисовка ---
    screen.blit(background_surface, (0, 0))

    if state in ("PLAY", "WIN", "LOSE"):
        for (wx, wy), b_type in walls.items():
            draw_wall_block(screen, wx, wy, b_type)

        if bonus_item:
            b_pos, b_type = bonus_item["pos"], bonus_item["type"]
            if b_type == "GOLD": draw_polygon_apple(screen, b_pos[0], b_pos[1], is_gold=True)
            else: draw_polygon_crystal(screen, b_pos[0], b_pos[1], b_type, now)

        draw_polygon_apple(screen, food[0], food[1])
        progress = min(1.0, (now - last_step) / cur_speed) if state == "PLAY" else 1.0
        draw_smooth_continuous_snake(screen, snake, prev_snake, direction, progress, is_frozen=is_frozen)

    # --- ВЕРХНЯЯ ПЛАШКА (HEADER) ---
    pygame.draw.rect(screen, CLR_HEADER, (0, 0, WIDTH, HEADER_HEIGHT))
    pygame.draw.line(screen, CLR_CARD_BORDER, (0, HEADER_HEIGHT), (WIDTH, HEADER_HEIGHT), 1)

    if game_mode == "CAMPAIGN":
        # Кампания: слева уровень, по центру прогресс-бар, справа FPS
        lvl_str = f"УР. {current_level}: {LEVELS[current_level]['name']}"
        lvl_txt = f_ui.render(lvl_str, True, CLR_ACCENT)
        screen.blit(lvl_txt, (MARGIN_SIDE, HEADER_HEIGHT // 2 - lvl_txt.get_height() // 2))

        if is_frozen and state == "PLAY":
            sec_left = max(0, int((freeze_end_time - now) / 1000) + 1)
            freeze_txt = f_sub.render(f"❄ ЗАМОРОЗКА: {sec_left}с", True, CLR_FREEZE)
            screen.blit(freeze_txt, (WIDTH // 2 - freeze_txt.get_width() // 2, HEADER_HEIGHT // 2 - freeze_txt.get_height() // 2))
        else:
            prog_w = int(WIDTH * 0.26)
            prog_x = (WIDTH - prog_w) // 2
            prog_y = HEADER_HEIGHT // 2 - 4
            pygame.draw.rect(screen, CLR_CARD, (prog_x, prog_y, prog_w, 8), border_radius=4)
            fill_w = int(prog_w * min(1.0, apples_eaten / LEVELS[current_level]["target"]))
            if fill_w > 0:
                pygame.draw.rect(screen, (52, 211, 153), (prog_x, prog_y, fill_w, 8), border_radius=4)

        fps_txt = f_sub.render(f"{int(clock.get_fps())}", True, CLR_MUTED)
        screen.blit(fps_txt, (WIDTH - MARGIN_SIDE - fps_txt.get_width(), HEADER_HEIGHT // 2 - fps_txt.get_height() // 2))

    else:
        # Бесконечный режим: РЕКОРД СЛЕВА, СЧЁТ СПРАВА
        rec_txt = f_ui.render(f"РЕКОРД: {endless_record}", True, CLR_GOLD)
        screen.blit(rec_txt, (MARGIN_SIDE, HEADER_HEIGHT // 2 - rec_txt.get_height() // 2))

        # Счёт справа
        score_txt = f_ui.render(f"СЧЁТ: {apples_eaten}", True, CLR_ACCENT)
        screen.blit(score_txt, (WIDTH - MARGIN_SIDE - score_txt.get_width(), HEADER_HEIGHT // 2 - score_txt.get_height() // 2))

        # Центр: статус заморозки либо FPS
        if is_frozen and state == "PLAY":
            sec_left = max(0, int((freeze_end_time - now) / 1000) + 1)
            freeze_txt = f_sub.render(f"❄ {sec_left}с", True, CLR_FREEZE)
            screen.blit(freeze_txt, (WIDTH // 2 - freeze_txt.get_width() // 2, HEADER_HEIGHT // 2 - freeze_txt.get_height() // 2))
        else:
            fps_txt = f_sub.render(f"{int(clock.get_fps())} FPS", True, CLR_MUTED)
            screen.blit(fps_txt, (WIDTH // 2 - fps_txt.get_width() // 2, HEADER_HEIGHT // 2 - fps_txt.get_height() // 2))

    # --- Меню SNAKEHUNT ---
    if state == "MENU":
        pygame.draw.rect(screen, CLR_BG, (0, HEADER_HEIGHT, WIDTH, HEIGHT - HEADER_HEIGHT))
        title_top = int(HEIGHT * 0.18)
        t = f_title.render("SNAKEHUNT", True, CLR_TEXT)
        t_glow = f_title.render("SNAKEHUNT", True, CLR_ACCENT)
        screen.blit(t_glow, t_glow.get_rect(center=(WIDTH // 2 + 2, title_top + 2)))
        screen.blit(t, t.get_rect(center=(WIDTH // 2, title_top)))

        rec_card_w, rec_card_h = int(WIDTH * 0.58), int(HEIGHT * 0.042)
        rec_card = pygame.Rect((WIDTH - rec_card_w) // 2, title_top + int(HEIGHT * 0.058), rec_card_w, rec_card_h)
        pygame.draw.rect(screen, CLR_CARD, rec_card, border_radius=12)
        pygame.draw.rect(screen, CLR_CARD_BORDER, rec_card, width=1, border_radius=12)
        st_rec = f_sub.render(f"🏆 РЕКОРД: {endless_record}  |  УРОВЕНЬ: {unlocked_level}/10", True, CLR_GOLD)
        screen.blit(st_rec, st_rec.get_rect(center=rec_card.center))

        pygame.draw.rect(screen, (14, 116, 144), play_rect.inflate(4, 4), border_radius=16)
        pygame.draw.rect(screen, CLR_ACCENT, play_rect, border_radius=14)
        b1 = f_card.render("КАМПАНИЯ", True, (10, 15, 26))
        screen.blit(b1, b1.get_rect(center=play_rect.center))

        pygame.draw.rect(screen, (161, 98, 7), endless_rect.inflate(4, 4), border_radius=16)
        pygame.draw.rect(screen, CLR_GOLD, endless_rect, border_radius=14)
        b_end = f_card.render("БЕСКОНЕЧНЫЙ РЕЖИМ", True, (10, 15, 26))
        screen.blit(b_end, b_end.get_rect(center=endless_rect.center))

        pygame.draw.rect(screen, CLR_BTN, lvl_btn_rect, border_radius=14)
        pygame.draw.rect(screen, CLR_CARD_BORDER, lvl_btn_rect, width=1, border_radius=14)
        b2 = f_card.render("ВЫБОР УРОВНЯ", True, CLR_TEXT)
        screen.blit(b2, b2.get_rect(center=lvl_btn_rect.center))

        pygame.draw.rect(screen, CLR_BTN, settings_btn_rect, border_radius=14)
        pygame.draw.rect(screen, CLR_CARD_BORDER, settings_btn_rect, width=1, border_radius=14)
        b3 = f_card.render("НАСТРОЙКИ", True, CLR_TEXT)
        screen.blit(b3, b3.get_rect(center=settings_btn_rect.center))

    elif state == "SETTINGS":
        pygame.draw.rect(screen, CLR_BG, (0, HEADER_HEIGHT, WIDTH, HEIGHT - HEADER_HEIGHT))
        st_title = f_card.render("НАСТРОЙКИ", True, CLR_TEXT)
        screen.blit(st_title, st_title.get_rect(center=(WIDTH // 2, HEIGHT * 0.24)))

        vol_label = f_ui.render(f"ГРОМКОСТЬ: {int(music_volume * 100)}%", True, CLR_ACCENT)
        screen.blit(vol_label, vol_label.get_rect(center=(WIDTH // 2, HEIGHT * 0.36)))

        pygame.draw.rect(screen, CLR_BTN, vol_minus_rect, border_radius=10)
        pygame.draw.rect(screen, CLR_CARD_BORDER, vol_minus_rect, width=1, border_radius=10)
        t_minus = f_card.render("-", True, CLR_TEXT)
        screen.blit(t_minus, t_minus.get_rect(center=vol_minus_rect.center))

        pygame.draw.rect(screen, CLR_BTN, vol_plus_rect, border_radius=10)
        pygame.draw.rect(screen, CLR_CARD_BORDER, vol_plus_rect, width=1, border_radius=10)
        t_plus = f_card.render("+", True, CLR_TEXT)
        screen.blit(t_plus, t_plus.get_rect(center=vol_plus_rect.center))

        pygame.draw.rect(screen, CLR_BTN, back_settings_rect, border_radius=14)
        pygame.draw.rect(screen, CLR_CARD_BORDER, back_settings_rect, width=1, border_radius=14)
        t_back = f_card.render("НАЗАД В МЕНЮ", True, CLR_TEXT)
        screen.blit(t_back, t_back.get_rect(center=back_settings_rect.center))

    elif state == "LEVEL_SELECT":
        pygame.draw.rect(screen, CLR_BG, (0, HEADER_HEIGHT, WIDTH, HEIGHT - HEADER_HEIGHT))
        lt = f_card.render("ВЫБЕРИТЕ УРОВЕНЬ", True, CLR_TEXT)
        screen.blit(lt, lt.get_rect(center=(WIDTH // 2, HEIGHT * 0.13)))

        cols, bw, bh = 2, int(WIDTH * 0.40), int(HEIGHT * 0.07)
        gap_x, gap_y = int(WIDTH * 0.05), int(HEIGHT * 0.016)
        start_y = int(HEIGHT * 0.18)
        for i in range(1, 11):
            c, r = (i - 1) % cols, (i - 1) // cols
            rect = pygame.Rect(int(WIDTH * 0.075) + c * (bw + gap_x), start_y + r * (bh + gap_y), bw, bh)
            unlocked = i <= unlocked_level
            bg_col = CLR_CARD if unlocked else (14, 18, 28)
            border_col = CLR_ACCENT if i == current_level else (CLR_CARD_BORDER if unlocked else (22, 28, 40))
            pygame.draw.rect(screen, bg_col, rect, border_radius=12)
            pygame.draw.rect(screen, border_col, rect, width=2 if i == current_level else 1, border_radius=12)
            txt_col = CLR_TEXT if unlocked else CLR_MUTED
            label = f"{i}. {LEVELS[i]['name']}" if unlocked else "Заперто"
            num_surf = f_sub.render(label, True, txt_col)
            screen.blit(num_surf, num_surf.get_rect(center=rect.center))

    elif state == "WIN":
        pygame.draw.rect(screen, CLR_CARD, win_card_rect, border_radius=18)
        pygame.draw.rect(screen, CLR_GOLD, win_card_rect, width=2, border_radius=18)

        m1 = f_card.render("УРОВЕНЬ ПРОЙДЕН!", True, CLR_GOLD)
        screen.blit(m1, m1.get_rect(center=(WIDTH // 2, win_card_rect.y + int(win_card_h * 0.22))))

        pygame.draw.rect(screen, CLR_ACCENT, win_next_btn, border_radius=12)
        next_label = "СЛЕДУЮЩИЙ УРОВЕНЬ" if current_level < 10 else "ПРОЙТИ СНОВА"
        t_next = f_ui.render(next_label, True, (10, 15, 26))
        screen.blit(t_next, t_next.get_rect(center=win_next_btn.center))

        pygame.draw.rect(screen, CLR_BTN, win_menu_btn, border_radius=12)
        pygame.draw.rect(screen, CLR_CARD_BORDER, win_menu_btn, width=1, border_radius=12)
        t_menu = f_ui.render("В ГЛАВНОЕ МЕНЮ", True, CLR_TEXT)
        screen.blit(t_menu, t_menu.get_rect(center=win_menu_btn.center))

    elif state == "LOSE":
        pygame.draw.rect(screen, CLR_CARD, lose_card_rect, border_radius=18)
        pygame.draw.rect(screen, (244, 63, 94), lose_card_rect, width=2, border_radius=18)

        m1 = f_card.render("СТОЛКНОВЕНИЕ!", True, (244, 63, 94))
        screen.blit(m1, m1.get_rect(center=(WIDTH // 2, lose_card_rect.y + int(lose_card_h * 0.18))))

        if game_mode == "ENDLESS":
            res_txt = f_sub.render(f"Счёт: {apples_eaten}  |  Рекорд: {endless_record}", True, CLR_GOLD)
            screen.blit(res_txt, res_txt.get_rect(center=(WIDTH // 2, lose_card_rect.y + int(lose_card_h * 0.33))))
        else:
            res_txt = f_sub.render(f"Собрано: {apples_eaten} / {LEVELS[current_level]['target']}", True, CLR_TEXT)
            screen.blit(res_txt, res_txt.get_rect(center=(WIDTH // 2, lose_card_rect.y + int(lose_card_h * 0.33))))

        pygame.draw.rect(screen, (244, 63, 94), lose_restart_btn, border_radius=12)
        t_restart = f_ui.render("ИГРАТЬ СНОВА", True, CLR_TEXT)
        screen.blit(t_restart, t_restart.get_rect(center=lose_restart_btn.center))

        pygame.draw.rect(screen, CLR_BTN, lose_menu_btn, border_radius=12)
        pygame.draw.rect(screen, CLR_CARD_BORDER, lose_menu_btn, width=1, border_radius=12)
        t_menu = f_ui.render("В ГЛАВНОЕ МЕНЮ", True, CLR_TEXT)
        screen.blit(t_menu, t_menu.get_rect(center=lose_menu_btn.center))

    pygame.display.flip()
    clock.tick(144)
