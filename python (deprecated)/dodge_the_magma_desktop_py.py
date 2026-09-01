import os
import ctypes
import math
import pygame
import random
import sys
import json
import platform
from functools import lru_cache

IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
	ctypes.windll.user32.SetProcessDPIAware()
pygame.init()

# ---------- SAVE ----------
SAVE_FILE = "save.json"
TARGET_FPS = 60
FRAME_MS = 1000 / TARGET_FPS
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
MIN_WIDTH = 640
MIN_HEIGHT = 480
GROUND_OFFSET = 90
PLAYER_SIZE = 50
MAGMA_SIZE = 30
COIN_SIZE = 20
DASH_SPEED = 19
MAGMA_BASE_SPEED = 6.2
MAGMA_MAX_SPEED = 13
MAGMA_SCORE_SCALE = 0.06
COIN_FALL_SPEED = 5
SHOP_ITEMS = [
	{
		"key": pygame.K_1,
		"label": "1",
		"title": "SPEED +1",
		"cost": 20,
		"color": (100, 200, 255),
		"desc": "Faster movement",
	},
	{
		"key": pygame.K_2,
		"label": "2",
		"title": "JUMP -2",
		"cost": 30,
		"color": (80, 255, 120),
		"desc": "Stronger jump",
	},
	{
		"key": pygame.K_3,
		"label": "3",
		"title": "SHIELD UPGRADE",
		"cost": 100,
		"color": (255, 220, 70),
		"desc": "Longer shield",
	},
	{
		"key": pygame.K_4,
		"label": "4",
		"title": "MAGNET UPGRADE",
		"cost": 150,
		"color": (255, 100, 255),
		"desc": "Pulls coins to you",
	},
]

coins = 0
player_speed = 8
jump_strength = -22
shield_cooldown_real = 300
shield_time_real = 120
magnet_level = 0
save_dirty = False
last_save_tick = 0
AUTO_SAVE_INTERVAL = 5000
magma_glow_surface = None
ui_scale_str = "Auto"


def save_game():
	global save_dirty, last_save_tick
	data = {
		"coins": coins,
		"player_speed": player_speed,
		"jump_strength": jump_strength,
		"shield_cooldown_real": shield_cooldown_real,
		"shield_time_real": shield_time_real,
		"magnet_level": magnet_level,
		"target_fps": TARGET_FPS,
		"ui_scale_str": ui_scale_str,
	}
	temp_file = f"{SAVE_FILE}.tmp"
	with open(temp_file, "w") as f:
		json.dump(data, f)
		f.flush()
		os.fsync(f.fileno())
	os.replace(temp_file, SAVE_FILE)
	save_dirty = False
	last_save_tick = pygame.time.get_ticks()


def queue_save():
	global save_dirty
	save_dirty = True


def load_game():
	global coins, player_speed, jump_strength
	global shield_cooldown_real, shield_time_real, magnet_level
	global TARGET_FPS, FRAME_MS, ui_scale_str
	try:
		with open(SAVE_FILE, "r") as f:
			data = json.load(f)
			coins = data.get("coins", coins)
			player_speed = data.get("player_speed", player_speed)
			jump_strength = data.get("jump_strength", jump_strength)
			shield_cooldown_real = data.get(
				"shield_cooldown_real", shield_cooldown_real
			)
			shield_time_real = data.get("shield_time_real", shield_time_real)
			magnet_level = data.get("magnet_level", magnet_level)
			TARGET_FPS = data.get("target_fps", TARGET_FPS)
			FRAME_MS = 1000 / TARGET_FPS
			ui_scale_str = data.get("ui_scale_str", ui_scale_str)
	except Exception:
		save_game()


def apply_display_settings(new_full, new_w, new_h, scale_str):
	global fullscreen, window_w, window_h, WIDTH, HEIGHT, ui_scale_str, screen, display_screen
	ui_scale_str = scale_str
	fullscreen = new_full
	window_w = new_w
	window_h = new_h
	
	if fullscreen:
		display_screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
		window_w, window_h = display_screen.get_size()
	else:
		display_screen = pygame.display.set_mode((window_w, window_h))
		
	scale_factor = 1.0
	if scale_str == "Auto":
		if window_w >= 3840: scale_factor = 2.0
		elif window_w >= 2560: scale_factor = 1.5
		elif window_w >= 1920: scale_factor = 1.25
		else: scale_factor = 1.0
	else:
		try:
			scale_factor = float(scale_str.replace('%', '')) / 100.0
		except ValueError:
			scale_factor = 1.0
			
	WIDTH = int(window_w / scale_factor)
	HEIGHT = int(window_h / scale_factor)
	screen = pygame.Surface((WIDTH, HEIGHT))


def get_safe_window_resolution():
	display_info = pygame.display.Info()
	max_width = max(MIN_WIDTH, display_info.current_w - 120)
	max_height = max(MIN_HEIGHT, display_info.current_h - 120)
	try:
		raw = input("Resolution: ").split()
		width, height = map(int, raw[:2])
	except Exception:
		width, height = DEFAULT_WIDTH, DEFAULT_HEIGHT

	if width <= 0 or height <= 0:
		width, height = DEFAULT_WIDTH, DEFAULT_HEIGHT

	width = max(MIN_WIDTH, min(max_width, width))
	height = max(MIN_HEIGHT, min(max_height, height))
	return width, height


def run_startup_screen(startup):
	"""Tra ve (width, height, fullscreen: bool)."""
	presets = [(1280, 720), (1600, 900), (1920, 1080)]
	selected_preset = 0
	fullscreen = False
	custom_w = "1280"
	custom_h = "720"
	active_field = None

	f_title = pygame.font.SysFont("Consolas", 26)
	f_med = pygame.font.SysFont("Consolas", 18)
	f_small = pygame.font.SysFont("Consolas", 14)

	def draw_btn(surf, rect, label, active, color=WHITE):
		bg = (10, 16, 32) if active else (17, 17, 34)
		border = color if active else (58, 58, 90)
		text_color = color if active else (100, 100, 130)
		pygame.draw.rect(surf, bg, rect, border_radius=6)
		pygame.draw.rect(surf, border, rect, 1, border_radius=6)
		text_surface = f_small.render(label, True, text_color)
		surf.blit(text_surface, text_surface.get_rect(center=rect.center))

	while True:
		startup.fill(BG)
		for x in range(0, 560, 40):
			pygame.draw.line(startup, GRID, (x, 0), (x, 380))
		for y in range(0, 380, 40):
			pygame.draw.line(startup, GRID, (0, y), (560, y))

		panel = pygame.Rect(80, 40, 400, 300)
		pygame.draw.rect(startup, (0, 0, 0), panel, border_radius=10)
		pygame.draw.rect(startup, WHITE, panel, 1, border_radius=10)

		title = f_title.render("DODGE THE MAGMA", True, WHITE)
		startup.blit(title, title.get_rect(centerx=280, y=58))

		startup.blit(f_small.render("DISPLAY MODE", True, (140, 140, 180)), (100, 100))

		btn_window = pygame.Rect(100, 118, 175, 32)
		btn_full = pygame.Rect(285, 118, 175, 32)
		draw_btn(startup, btn_window, "WINDOW", not fullscreen, BLUE)
		draw_btn(startup, btn_full, "FULLSCREEN", fullscreen, BLUE)

		res_alpha = 80 if fullscreen else 255
		resolution_label = f_small.render("RESOLUTION", True, (140, 140, 180))
		resolution_label.set_alpha(res_alpha)
		startup.blit(resolution_label, (100, 164))

		preset_rects = []
		for i, (preset_w, preset_h) in enumerate(presets):
			rect = pygame.Rect(100 + i * 120, 182, 110, 28)
			preset_rects.append(rect)
			if not fullscreen:
				draw_btn(startup, rect, f"{preset_w}x{preset_h}", selected_preset == i, GREEN)
			else:
				pygame.draw.rect(startup, (17, 17, 34), rect, border_radius=6)
				pygame.draw.rect(startup, (40, 40, 60), rect, 1, border_radius=6)

		custom_rect = pygame.Rect(100, 218, 80, 28)
		if not fullscreen:
			draw_btn(startup, custom_rect, "custom", selected_preset == -1, GREEN)

		width_rect = None
		height_rect = None
		if selected_preset == -1 and not fullscreen:
			width_rect = pygame.Rect(100, 254, 80, 28)
			height_rect = pygame.Rect(200, 254, 80, 28)
			for rect, value, field in (
				(width_rect, custom_w, "w"),
				(height_rect, custom_h, "h"),
			):
				border = BLUE if active_field == field else (58, 58, 90)
				pygame.draw.rect(startup, (11, 11, 22), rect, border_radius=6)
				pygame.draw.rect(startup, border, rect, 1, border_radius=6)
				value_surface = f_med.render(value, True, WHITE)
				startup.blit(value_surface, value_surface.get_rect(center=rect.center))
			startup.blit(f_small.render("x", True, (80, 80, 110)), (188, 262))

		launch_rect = pygame.Rect(100, 294, 360, 36)
		pygame.draw.rect(startup, (0, 0, 0), launch_rect, border_radius=8)
		pygame.draw.rect(startup, WHITE, launch_rect, 1, border_radius=8)
		launch_text = f_med.render("[ LAUNCH ]", True, WHITE)
		startup.blit(launch_text, launch_text.get_rect(center=launch_rect.center))

		pygame.display.flip()

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				pygame.quit()
				sys.exit()

			if event.type == pygame.MOUSEBUTTONDOWN:
				mouse_x, mouse_y = event.pos
				if btn_window.collidepoint(mouse_x, mouse_y):
					fullscreen = False
				if btn_full.collidepoint(mouse_x, mouse_y):
					fullscreen = True
					active_field = None
				if not fullscreen:
					for i, rect in enumerate(preset_rects):
						if rect.collidepoint(mouse_x, mouse_y):
							selected_preset = i
							active_field = None
					if custom_rect.collidepoint(mouse_x, mouse_y):
						selected_preset = -1
					if selected_preset == -1:
						if width_rect and width_rect.collidepoint(mouse_x, mouse_y):
							active_field = "w"
						elif height_rect and height_rect.collidepoint(mouse_x, mouse_y):
							active_field = "h"
						else:
							active_field = None
				if launch_rect.collidepoint(mouse_x, mouse_y):
					if fullscreen:
						return 0, 0, True
					if selected_preset >= 0:
						preset_w, preset_h = presets[selected_preset]
						return preset_w, preset_h, False
					try:
						return int(custom_w), int(custom_h), False
					except ValueError:
						pass

			if event.type == pygame.KEYDOWN:
				if active_field == "w":
					if event.key == pygame.K_BACKSPACE:
						custom_w = custom_w[:-1]
					elif event.unicode.isdigit() and len(custom_w) < 4:
						custom_w += event.unicode
					elif event.key == pygame.K_TAB:
						active_field = "h"
				elif active_field == "h":
					if event.key == pygame.K_BACKSPACE:
						custom_h = custom_h[:-1]
					elif event.unicode.isdigit() and len(custom_h) < 4:
						custom_h += event.unicode
					elif event.key == pygame.K_TAB:
						active_field = "w"
				if event.key == pygame.K_RETURN:
					if fullscreen:
						return 0, 0, True
					if selected_preset >= 0:
						preset_w, preset_h = presets[selected_preset]
						return preset_w, preset_h, False
					try:
						return int(custom_w), int(custom_h), False
					except ValueError:
						pass


# ---------- SCREEN ----------
WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT

WHITE = (255, 255, 255)
RED = (255, 80, 70)
ORANGE = (255, 160, 60)
BLUE = (100, 200, 255)
GREEN = (80, 255, 120)
YELLOW = (255, 220, 70)
PURPLE = (160, 130, 255)
BG = (10, 10, 20)
GRID = (30, 30, 60)
PANEL = (0, 0, 0)
CONSOLE_BG = (0, 0, 0, 210)
CONSOLE_TEXT = (200, 200, 220)
CONSOLE_CMD = (100, 200, 255)
CONSOLE_OK = (80, 255, 120)
CONSOLE_ERR = (255, 80, 70)
CONSOLE_INFO = (140, 140, 180)
CONSOLE_MAX_LINES = 12

clock = pygame.time.Clock()
font = pygame.font.SysFont("Consolas", 28)
small_font = pygame.font.SysFont("Consolas", 22)
big_font = pygame.font.SysFont("Consolas", 48)

startup_screen = pygame.display.set_mode((560, 380))
pygame.display.set_caption("DODGE THE MAGMA")
start_w, start_h, fullscreen = run_startup_screen(startup_screen)

pygame.quit()
pygame.init()
clock = pygame.time.Clock()
font = pygame.font.SysFont("Consolas", 28)
small_font = pygame.font.SysFont("Consolas", 22)
big_font = pygame.font.SysFont("Consolas", 48)


load_game()

display_info = pygame.display.Info()
init_w = max(MIN_WIDTH, min(start_w, display_info.current_w - 120))
init_h = max(MIN_HEIGHT, min(start_h, display_info.current_h - 120))
display_screen = None
apply_display_settings(fullscreen, init_w, init_h, ui_scale_str)

pygame.display.set_caption("DODGE THE MAGMA")
if IS_WINDOWS:
	window_info = pygame.display.get_wm_info()
	hwnd = window_info.get("window")
	if hwnd:
		SWP_NOSIZE = 0x0001
		SWP_NOMOVE = 0x0002
		HWND_TOPMOST = -1
		HWND_NOTOPMOST = -2
		ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
		ctypes.windll.user32.SetForegroundWindow(hwnd)
		ctypes.windll.user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

load_game()

# ---------- HELPERS ----------
def clamp(value, minimum, maximum):
	return max(minimum, min(maximum, value))


def draw_box(x, y, w, h, color=PANEL, border=WHITE, border_radius=10):
	pygame.draw.rect(screen, color, (x, y, w, h), border_radius=border_radius)
	pygame.draw.rect(
		screen, border, (x, y, w, h), 2, border_radius=border_radius
	)


def draw_text(text, y, color=WHITE, font_ref=font):
	rendered = font_ref.render(text, True, color)
	screen.blit(rendered, (WIDTH // 2 - rendered.get_width() // 2, y))


def draw_bar(x, y, w, h, ratio, fill_color, label, border_color=WHITE):
	ratio = clamp(ratio, 0, 1)
	pygame.draw.rect(screen, (25, 25, 35), (x, y, w, h), border_radius=8)
	pygame.draw.rect(screen, border_color, (x, y, w, h), 2, border_radius=8)
	if ratio > 0:
		inner_w = max(0, int((w - 4) * ratio))
		pygame.draw.rect(
			screen,
			fill_color,
			(x + 2, y + 2, inner_w, h - 4),
			border_radius=7,
		)
	label_surf = small_font.render(label, True, WHITE)
	screen.blit(label_surf, (x + 8, y + h // 2 - label_surf.get_height() // 2))


@lru_cache(maxsize=64)
def get_glow_surface(radius, color, alpha):
	surface = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
	pygame.draw.circle(
		surface, (*color, alpha), (radius * 2, radius * 2), radius
	)
	pygame.draw.circle(
		surface,
		(*color, alpha // 2),
		(radius * 2, radius * 2),
		int(radius * 1.5),
	)
	return surface


def get_magma_glow_surface():
	global magma_glow_surface
	if magma_glow_surface is None:
		magma_glow_surface = pygame.Surface((72, 72), pygame.SRCALPHA)
		pygame.draw.circle(magma_glow_surface, (255, 110, 50, 80), (36, 36), 18)
		pygame.draw.circle(magma_glow_surface, (255, 70, 40, 50), (36, 36), 26)
	return magma_glow_surface


@lru_cache(maxsize=96)
def get_trail_surface(size, alpha):
	surface = pygame.Surface((size[0] + 30, size[1] + 30), pygame.SRCALPHA)
	pygame.draw.rect(
		surface,
		(120, 210, 255, alpha),
		(15, 15, size[0], size[1]),
		border_radius=12,
	)
	return surface


def draw_glow_circle(center, radius, color, alpha=70):
	glow = get_glow_surface(radius, color, alpha)
	screen.blit(glow, (center[0] - radius * 2, center[1] - radius * 2))


def reset_run():
	global score, game_state, velocity_y, jumps_left, jump_hold_time
	global player_vx, player_pos_x, player_pos_y, coyote_time, jump_buffer_time
	global dash_velocity, dash_duration, dash_cooldown, dash_trail
	global shield, shield_time, shield_cooldown, shield_flash
	global magma_list, coin_list, next_magma_spawn, next_coin_spawn
	global player, facing, gameover_input_unlock_at

	score = 0
	game_state = "game"
	gameover_input_unlock_at = 0
	player.x = WIDTH // 2
	player.bottom = HEIGHT - GROUND_OFFSET
	player_pos_x = float(player.x)
	player_pos_y = float(player.y)
	velocity_y = 0.0
	player_vx = 0.0
	jumps_left = max_jumps
	jump_hold_time = 0
	coyote_time = 0
	jump_buffer_time = 0
	dash_velocity = 0.0
	dash_duration = 0
	dash_cooldown = 0
	dash_trail = []
	shield = False
	shield_time = 0
	shield_cooldown = 0
	shield_flash = 0
	magma_list.clear()
	coin_list.clear()
	facing = 1
	now = pygame.time.get_ticks()
	next_magma_spawn = now + 300
	next_coin_spawn = now + 900


def spawn_magma_pattern():
	pattern = random.choices(
		["single", "double", "cluster", "zigzag"],
		weights=[45, 20, 25, 10],
		k=1,
	)[0]
	spawn_x = random.randint(20, max(20, WIDTH - 50))
	pieces = []

	if pattern == "single":
		pieces.append(pygame.Rect(spawn_x, -30, 30, 30))
	elif pattern == "double":
		offset = random.choice([40, 55])
		pieces.append(pygame.Rect(clamp(spawn_x, 0, WIDTH - MAGMA_SIZE), -MAGMA_SIZE, MAGMA_SIZE, MAGMA_SIZE))
		pieces.append(
			pygame.Rect(clamp(spawn_x + offset, 0, WIDTH - MAGMA_SIZE), -MAGMA_SIZE, MAGMA_SIZE, MAGMA_SIZE)
		)
	elif pattern == "cluster":
		offsets = [-44, -12, 20, 52]
		for off in random.sample(offsets, k=random.randint(3, 4)):
			pieces.append(
				pygame.Rect(clamp(spawn_x + off, 0, WIDTH - MAGMA_SIZE), -MAGMA_SIZE, MAGMA_SIZE, MAGMA_SIZE)
			)
	else:
		lane = random.randint(0, 3)
		for i in range(4):
			x = clamp(spawn_x + (i - lane) * 34, 0, WIDTH - MAGMA_SIZE)
			pieces.append(pygame.Rect(x, -MAGMA_SIZE - i * 10, MAGMA_SIZE, MAGMA_SIZE))

	magma_list.extend(pieces)


def spawn_coin_pattern():
	pattern = random.choices(
		["single", "zigzag", "line", "reward"],
		weights=[42, 28, 20, 10],
		k=1,
	)[0]
	base_x = random.randint(15, max(15, WIDTH - 35))
	base_y = -20
	coins_to_add = []

	if pattern == "single":
		coins_to_add.append(pygame.Rect(base_x, base_y, COIN_SIZE, COIN_SIZE))
	elif pattern == "zigzag":
		for i in range(5):
			x = clamp(base_x + (-1) ** i * (18 + i * 2), 0, WIDTH - COIN_SIZE)
			y = base_y - i * 22
			coins_to_add.append(pygame.Rect(x, y, COIN_SIZE, COIN_SIZE))
	elif pattern == "line":
		for i in range(4):
			x = clamp(base_x + i * 26, 0, WIDTH - COIN_SIZE)
			coins_to_add.append(pygame.Rect(x, base_y - i * 8, COIN_SIZE, COIN_SIZE))
	else:
		for i in range(3):
			x = clamp(base_x + i * 34 - 34, 0, WIDTH - COIN_SIZE)
			y = base_y - abs(i - 1) * 18
			coins_to_add.append(pygame.Rect(x, y, COIN_SIZE, COIN_SIZE))

	coin_list.extend(coins_to_add)


def draw_player():
	body_color = BLUE if not shield else (135, 240, 255)
	lean = int(clamp(velocity_y / 4, -4, 4))
	body = pygame.Rect(player.x, player.y, player.width, player.height)
	body.inflate_ip(-4, -4)

	pygame.draw.rect(
		screen,
		(20, 40, 65),
		body.move(0, 4),
		border_radius=14,
	)
	pygame.draw.rect(
		screen,
		body_color,
		body.move(lean, 0),
		border_radius=14,
	)

	eye_x = body.centerx + (7 if facing > 0 else -14)
	pygame.draw.rect(
		screen,
		WHITE,
		(eye_x, body.y + 12, 5, 5),
		border_radius=2,
	)
	pygame.draw.rect(
		screen,
		(20, 20, 30),
		(eye_x + 1, body.y + 13, 2, 2),
		border_radius=1,
	)


def draw_magma(m):
	glow = get_magma_glow_surface()
	screen.blit(glow, (m.centerx - 36, m.centery - 36))

	pygame.draw.rect(screen, (130, 35, 20), m.inflate(-4, -4), border_radius=6)
	pygame.draw.rect(screen, RED, m, border_radius=6)
	pygame.draw.rect(screen, ORANGE, m.inflate(-14, -14), border_radius=4)


def draw_coin(c, tick):
	pulse = 1 + int((math.sin(tick * 0.02) + 1) * 1.5)
	pygame.draw.circle(screen, (200, 160, 20), c.center, 11 + pulse // 3)
	pygame.draw.circle(screen, YELLOW, c.center, 8 + pulse // 4)
	pygame.draw.circle(screen, WHITE, (c.centerx - 3, c.centery - 3), 2)
	pygame.draw.line(
		screen, WHITE, (c.centerx - 6, c.centery), (c.centerx + 6, c.centery), 1
	)
	pygame.draw.line(
		screen, WHITE, (c.centerx, c.centery - 6), (c.centerx, c.centery + 6), 1
	)


# ---------- PLAYER ----------
player = pygame.Rect(WIDTH // 2, HEIGHT - 100, PLAYER_SIZE, PLAYER_SIZE)
player_pos_x = float(player.x)
player_pos_y = float(player.y)
velocity_y = 0.0
player_vx = 0.0
gravity = 1.35
run_accel = 0.9
run_friction = 0.80
run_max_speed = player_speed
max_jumps = 2
jumps_left = max_jumps
jump_hold_max = 12
jump_hold_time = 0
facing = 1
coyote_max = 6
coyote_time = 0
jump_buffer_max = 6
jump_buffer_time = 0


# ---------- DASH ----------
dash_velocity = 0.0
dash_duration = 0
dash_cooldown = 0
dash_trail = []
dash_trail_timer = 0


# ---------- SHIELD ----------
shield = False
shield_time = 0
shield_cooldown = 0
shield_flash = 0


# ---------- OBJECTS ----------
magma_list = []
coin_list = []
next_magma_spawn = pygame.time.get_ticks() + 300
next_coin_spawn = pygame.time.get_ticks() + 900

score = 0
game_state = "menu"
gameover_input_unlock_at = 0
console_open = False
console_input = ""
console_log = []

settings_presets = [(1280, 720), (1600, 900), (1920, 1080)]
settings_selected_preset = -1
settings_custom_w = str(window_w)
settings_custom_h = str(window_h)
settings_active_field = None
settings_fullscreen = False
settings_fps = TARGET_FPS
settings_ui_scale_opts = ["Auto", "100%", "125%", "150%", "175%", "200%"]
settings_scale_str = "Auto"


def update_timer(value, amount):
	return max(0.0, value - amount)


def console_exec(cmd):
	global coins, player_speed, jump_strength
	global shield, shield_time
	global shield_cooldown_real, shield_time_real
	
	# Tách lệnh và tham số
	parts = cmd.strip().lower().split()
	if not parts:
		return None
	
	command = parts[0]
	arg = parts[1] if len(parts) > 1 else None

	if command == "coin":
		amount = int(arg) if arg and arg.isdigit() else 100  # default 100
		coins += amount
		queue_save()
		return (f"+{amount} coins", CONSOLE_OK)

	if command == "speed":
		amount = int(arg) if arg and arg.isdigit() else 2    # default +2
		player_speed += amount
		queue_save()
		return (f"speed -> {player_speed}", CONSOLE_OK)

	if command == "jump":
		amount = int(arg) if arg and arg.isdigit() else 2    # default +2
		jump_strength -= amount
		queue_save()
		return (f"jump -> {jump_strength}", CONSOLE_OK)

	if command == "god":
		shield = True
		shield_time = 999999
		return ("god mode ON", CONSOLE_OK)
	if command == "reset":
		if arg == "jump":
			jump_strength = -22
			queue_save()
			return ("jump reset", CONSOLE_OK)
		if arg == "coin":
			coins = 0
			queue_save()
			return ("coins reset", CONSOLE_OK)
		if arg == "speed":
			player_speed = 8
			queue_save()
			return ("speed reset", CONSOLE_OK)
		if arg == "shield":
			shield_cooldown_real = 300
			shield_time_real = 120
			queue_save()
			return ("shield reset", CONSOLE_OK)
		if arg == "all" or arg is None:
			coins = 0
			player_speed = 8
			shield_cooldown_real = 300
			shield_time_real = 120
			queue_save()
			return ("full reset done", CONSOLE_OK)
		return (f"reset: unknown target '{arg}'", CONSOLE_ERR)

	if command == "help":
		return ("money [n] | speed [n] | god | reset [coins/speed/shield/all] | save | exit", CONSOLE_INFO)

	if command == "exit":
		save_game()
		pygame.quit()
		sys.exit()

	if command == "save":
		save_game()
		return ("saved to save.json", CONSOLE_OK)
	
	if command == "stats":
		return (f"coins: {coins}, speed: {player_speed}, jump: {jump_strength}, shield_cd: {shield_cooldown_real}, shield_time: {shield_time_real}", CONSOLE_INFO)

	return (f"unknown: {command}", CONSOLE_ERR)

def draw_console():
	h = 180
	y0 = HEIGHT - h
	overlay = pygame.Surface((WIDTH, h), pygame.SRCALPHA)
	overlay.fill(CONSOLE_BG)
	screen.blit(overlay, (0, y0))
	pygame.draw.line(screen, (60, 60, 120), (0, y0), (WIDTH, y0), 1)

	header = small_font.render("CHEAT CONSOLE  [ ESC close ]", True, CONSOLE_INFO)
	screen.blit(header, (14, y0 + 8))

	line_h = 22
	input_y = HEIGHT - 30
	max_display_lines = (input_y - 4 - (y0 + 32)) // line_h  # tính động theo chiều cao thực tế

	# Lấy đúng số dòng hiển thị được, tính từ cuối — đây là chỗ "auto-scroll"
	visible_logs = console_log[-max_display_lines:]

	# Render từ dưới lên để log mới nhất luôn sát input
	start_y = input_y - 4 - len(visible_logs) * line_h
	for i, (text, color) in enumerate(visible_logs):
		line_surface = small_font.render(text, True, color)
		screen.blit(line_surface, (14, start_y + i * line_h))

	pygame.draw.line(screen, (60, 60, 120), (0, input_y - 4), (WIDTH, input_y - 4), 1)
	prompt = small_font.render("$ " + console_input, True, CONSOLE_CMD)
	screen.blit(prompt, (14, input_y))

	if (pygame.time.get_ticks() // 500) % 2 == 0:
		cursor_x = 14 + prompt.get_width() + 2
		pygame.draw.rect(screen, CONSOLE_CMD, (cursor_x, input_y + 2, 2, 18))


# ---------- UI ----------
def draw_hud():
	panel_x = 10
	panel_y = 10
	draw_box(panel_x, panel_y, 320, 108, (0, 0, 0), WHITE)

	score_surf = font.render(f"SCORE: {score}", True, WHITE)
	coin_surf = font.render(f"COINS: {coins}", True, YELLOW)
	speed_surf = small_font.render(f"SPD: {player_speed}", True, BLUE)
	jump_surf = small_font.render(f"JUMPS: {jumps_left}/{max_jumps}", True, GREEN)
	screen.blit(score_surf, (22, 20))
	screen.blit(coin_surf, (22, 52))
	screen.blit(speed_surf, (22, 90))
	screen.blit(jump_surf, (150, 90))


def draw_ability_bar():
	icon_size = 34
	bar_w = 110
	bar_h = 12
	slot_gap = 24
	icon_bar_gap = 10
	slot_w = icon_size + icon_bar_gap + bar_w

	slots = [
		{
			"label": "DASH",
			"key": "[Q]",
			"ratio": 1.0 if dash_cooldown <= 0 else 1 - dash_cooldown / 60,
			"color": BLUE,
			"active": dash_cooldown <= 0,
		},
		{
			"label": "SHIELD",
			"key": "[E]",
			"ratio": 1.0 if shield_cooldown <= 0 else 1 - shield_cooldown / shield_cooldown_real,
			"color": GREEN,
			"active": shield or shield_cooldown <= 0,
		},
	]

	total_w = slot_w * 2 + slot_gap
	start_x = WIDTH // 2 - total_w // 2
	center_y = HEIGHT - 55

	for i, slot in enumerate(slots):
		x = start_x + i * (slot_w + slot_gap)

		# --- icon: can giua doc ---
		icon_y = center_y - icon_size // 2
		icon_border = slot["color"] if slot["active"] else (58, 58, 90)
		icon_bg = (10, 22, 12) if slot["color"] == GREEN else (10, 16, 32)
		icon_bg = icon_bg if slot["active"] else (17, 17, 34)
		pygame.draw.rect(screen, icon_bg, (x, icon_y, icon_size, icon_size), border_radius=6)
		pygame.draw.rect(screen, icon_border, (x, icon_y, icon_size, icon_size), 1, border_radius=6)

		if slot["active"]:
			pygame.draw.circle(screen, slot["color"], (x + icon_size - 6, icon_y + 6), 3)

		# --- text + bar: ben phai icon ---
		bar_x = x + icon_size + icon_bar_gap

		label_h = small_font.get_height()
		key_h = small_font.get_height()
		content_h = label_h + 4 + bar_h + 4 + key_h
		text_y = center_y - content_h // 2

		label_surface = small_font.render(slot["label"], True, (180, 180, 210))
		screen.blit(label_surface, (bar_x, text_y))

		bar_y = text_y + label_h + 4
		pygame.draw.rect(screen, (26, 26, 46), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
		pygame.draw.rect(screen, (58, 58, 90), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=6)

		fill_w = max(0, int(bar_w * clamp(slot["ratio"], 0, 1)))
		if fill_w > 0:
			pygame.draw.rect(screen, slot["color"], (bar_x, bar_y, fill_w, bar_h), border_radius=6)

		key_surface = small_font.render(slot["key"], True, (90, 90, 120))
		screen.blit(key_surface, (bar_x, bar_y + bar_h + 4))


def draw_info_hub():
	hub_w = 220
	hub_h = 72
	hub_x = WIDTH - hub_w - 12
	hub_y = 12
	draw_box(hub_x, hub_y, hub_w, hub_h, (0, 0, 0), WHITE)

	coins_surf = small_font.render(f"COINS: {coins}", True, YELLOW)
	score_surf = small_font.render(f"SCORE: {score}", True, WHITE)
	screen.blit(coins_surf, (hub_x + 16, hub_y + 14))
	screen.blit(score_surf, (hub_x + 16, hub_y + 40))


def draw_menu():
	draw_box(WIDTH // 2 - 260, 170, 520, 400, (0, 0, 0), WHITE)

	y = 210
	gap = 42

	screen.blit(
		big_font.render("DODGE THE MAGMA", True, WHITE),
		(WIDTH // 2 - 230, y),
	)
	y += 72

	draw_text("[ SPACE ] START", y, BLUE)
	y += gap
	draw_text("[ S ] SHOP", y, GREEN)
	y += gap
	draw_text("[ O ] SETTINGS", y, PURPLE)
	y += gap
	draw_text("[ Q ] EXIT", y, RED)
	y += gap
	draw_text(f"COINS: {coins}", y, YELLOW)


def get_settings_rects():
	px = WIDTH // 2 - 300
	py = 150
	
	btn_window = pygame.Rect(px + 40, py + 60, 175, 32)
	btn_full = pygame.Rect(px + 225, py + 60, 175, 32)
	
	preset_rects = []
	for i in range(len(settings_presets)):
		rect = pygame.Rect(px + 40 + i * 120, py + 124, 110, 28)
		preset_rects.append(rect)
	
	custom_rect = pygame.Rect(px + 40, py + 160, 80, 28)
	width_rect = pygame.Rect(px + 40, py + 196, 80, 28)
	height_rect = pygame.Rect(px + 140, py + 196, 80, 28)
	
	fps_rects = []
	for i in range(4):
		rect = pygame.Rect(px + 40 + i * 90, py + 250, 80, 28)
		fps_rects.append(rect)
		
	scale_rects = []
	for i in range(6):
		rect = pygame.Rect(px + 40 + i * 80, py + 310, 70, 28)
		scale_rects.append(rect)
		
	apply_rect = pygame.Rect(px + 40, py + 360, 250, 40)
	back_rect = pygame.Rect(px + 310, py + 360, 250, 40)
	
	return btn_window, btn_full, preset_rects, custom_rect, width_rect, height_rect, apply_rect, back_rect, fps_rects, scale_rects


def draw_settings():
	px = WIDTH // 2 - 300
	py = 150
	draw_box(px, py, 600, 430, (0, 0, 0), WHITE)
	
	draw_text("=== SETTINGS ===", py + 15, PURPLE, small_font)
	
	f_small = pygame.font.SysFont("Consolas", 14)
	f_med = pygame.font.SysFont("Consolas", 18)
	
	def draw_btn(surf, rect, label, active, color=WHITE):
		bg = (10, 16, 32) if active else (17, 17, 34)
		border = color if active else (58, 58, 90)
		text_color = color if active else (100, 100, 130)
		pygame.draw.rect(surf, bg, rect, border_radius=6)
		pygame.draw.rect(surf, border, rect, 1, border_radius=6)
		text_surface = f_small.render(label, True, text_color)
		surf.blit(text_surface, text_surface.get_rect(center=rect.center))

	btn_window, btn_full, preset_rects, custom_rect, width_rect, height_rect, apply_rect, back_rect, fps_rects, scale_rects = get_settings_rects()
	
	screen.blit(f_small.render("DISPLAY MODE", True, (140, 140, 180)), (px + 40, py + 42))
	draw_btn(screen, btn_window, "WINDOW", not settings_fullscreen, BLUE)
	draw_btn(screen, btn_full, "FULLSCREEN", settings_fullscreen, BLUE)
	
	res_alpha = 80 if settings_fullscreen else 255
	resolution_label = f_small.render("RESOLUTION", True, (140, 140, 180))
	resolution_label.set_alpha(res_alpha)
	screen.blit(resolution_label, (px + 40, py + 106))
	
	for i, (preset_w, preset_h) in enumerate(settings_presets):
		if not settings_fullscreen:
			draw_btn(screen, preset_rects[i], f"{preset_w}x{preset_h}", settings_selected_preset == i, GREEN)
		else:
			pygame.draw.rect(screen, (17, 17, 34), preset_rects[i], border_radius=6)
			pygame.draw.rect(screen, (40, 40, 60), preset_rects[i], 1, border_radius=6)
			
	if not settings_fullscreen:
		draw_btn(screen, custom_rect, "custom", settings_selected_preset == -1, GREEN)
		
	if settings_selected_preset == -1 and not settings_fullscreen:
		for rect, value, field in (
			(width_rect, settings_custom_w, "w"),
			(height_rect, settings_custom_h, "h"),
		):
			border = BLUE if settings_active_field == field else (58, 58, 90)
			pygame.draw.rect(screen, (11, 11, 22), rect, border_radius=6)
			pygame.draw.rect(screen, border, rect, 1, border_radius=6)
			value_surface = f_med.render(value, True, WHITE)
			screen.blit(value_surface, value_surface.get_rect(center=rect.center))
		screen.blit(f_small.render("x", True, (80, 80, 110)), (px + 128, py + 204))

	screen.blit(f_small.render("TARGET FPS", True, (140, 140, 180)), (px + 40, py + 232))
	fps_options = [30, 60, 120, 144]
	for i, fps in enumerate(fps_options):
		draw_btn(screen, fps_rects[i], f"{fps} FPS", settings_fps == fps, GREEN)
		
	screen.blit(f_small.render("UI SCALE", True, (140, 140, 180)), (px + 40, py + 292))
	for i, scale_opt in enumerate(settings_ui_scale_opts):
		draw_btn(screen, scale_rects[i], scale_opt, settings_scale_str == scale_opt, GREEN)

	draw_btn(screen, apply_rect, "[ APPLY ]", True, WHITE)
	draw_btn(screen, back_rect, "[ BACK ]", True, RED)


def draw_shop():
	draw_box(WIDTH // 2 - 330, 110, 660, 480, (0, 0, 0), WHITE)

	real_mx, real_my = pygame.mouse.get_pos()
	scale_x = WIDTH / window_w
	scale_y = HEIGHT / window_h
	mouse = (int(real_mx * scale_x), int(real_my * scale_y))
	item_rects = []
	for i in range(len(SHOP_ITEMS)):
		item_rects.append(pygame.Rect(WIDTH // 2 - 250, 170 + i * 85, 500, 70))

	draw_text("=== SHOP ===", 130, YELLOW)

	for item, item_rect in zip(SHOP_ITEMS, item_rects):
		hovered = item_rect.collidepoint(mouse)
		fill = (28, 28, 40) if not hovered else (50, 50, 72)
		border = item["color"] if hovered else WHITE
		pygame.draw.rect(screen, fill, item_rect, border_radius=12)
		pygame.draw.rect(screen, border, item_rect, 2, border_radius=12)

		icon = small_font.render(f"[{item['label']}]", True, item["color"])
		title = font.render(item["title"], True, WHITE)
		cost = small_font.render(f"{item['cost']} coins", True, YELLOW)
		desc = small_font.render(item["desc"], True, (180, 180, 190))

		screen.blit(icon, (item_rect.x + 18, item_rect.y + 16))
		screen.blit(title, (item_rect.x + 78, item_rect.y + 12))
		screen.blit(desc, (item_rect.x + 78, item_rect.y + 38))
		screen.blit(cost, (item_rect.right - cost.get_width() - 18, item_rect.y + 23))

	draw_text("[ ESC ] BACK", 520, WHITE)
	draw_text(f"COINS: {coins}", 550, YELLOW)


def draw_pause():
	draw_box(WIDTH // 2 - 250, 180, 500, 260, (0, 0, 0), BLUE)
	draw_text("PAUSED", 225, BLUE, big_font)
	draw_text("[ ESC ] RESUME", 310, WHITE)
	draw_text("[ M ] MENU", 352, GREEN)
	draw_text("[ Q ] SAVE & QUIT", 394, RED)


def draw_gameover():
	draw_box(WIDTH // 2 - 260, 160, 520, 380, (0, 0, 0), RED)

	y = 200
	gap = 38

	screen.blit(
		big_font.render("GAME OVER", True, RED),
		(WIDTH // 2 - 150, y),
	)
	y += 72

	draw_text(f"SCORE: {score}", y, WHITE)
	y += gap
	draw_text(f"COINS: {coins}", y, YELLOW)
	y += gap
	draw_text("[ SPACE ] RETRY", y, BLUE)
	y += gap
	draw_text("[ M ] MENU", y, GREEN)
	y += gap
	draw_text("[ S ] SHOP", y, YELLOW)
	y += gap
	draw_text("[ Q ] EXIT", y, WHITE)
	if pygame.time.get_ticks() < gameover_input_unlock_at:
		draw_text("Please wait...", y + 36, (180, 180, 180), small_font)


# ---------- LOOP ----------
while True:
	dt = clock.tick(TARGET_FPS) / FRAME_MS
	tick = pygame.time.get_ticks()

	# background grid
	screen.fill(BG)
	for x in range(0, WIDTH, 40):
		pygame.draw.line(screen, GRID, (x, 0), (x, HEIGHT))
	for y in range(0, HEIGHT, 40):
		pygame.draw.line(screen, GRID, (0, y), (WIDTH, y))

	if save_dirty and tick - last_save_tick >= AUTO_SAVE_INTERVAL:
		save_game()

	# ---------- EVENTS ----------
	for e in pygame.event.get():
		if e.type == pygame.QUIT:
			save_game()
			pygame.quit()
			sys.exit()

		if e.type == pygame.MOUSEBUTTONDOWN and game_state == "settings":
			mouse_x, mouse_y = e.pos
			scale_x = WIDTH / window_w
			scale_y = HEIGHT / window_h
			mouse_x = int(mouse_x * scale_x)
			mouse_y = int(mouse_y * scale_y)
			btn_window, btn_full, preset_rects, custom_rect, width_rect, height_rect, apply_rect, back_rect, fps_rects, scale_rects = get_settings_rects()
			
			if btn_window.collidepoint(mouse_x, mouse_y):
				settings_fullscreen = False
			if btn_full.collidepoint(mouse_x, mouse_y):
				settings_fullscreen = True
				settings_active_field = None
			if not settings_fullscreen:
				for i, rect in enumerate(preset_rects):
					if rect.collidepoint(mouse_x, mouse_y):
						settings_selected_preset = i
						settings_active_field = None
				if custom_rect.collidepoint(mouse_x, mouse_y):
					settings_selected_preset = -1
				if settings_selected_preset == -1:
					if width_rect and width_rect.collidepoint(mouse_x, mouse_y):
						settings_active_field = "w"
					elif height_rect and height_rect.collidepoint(mouse_x, mouse_y):
						settings_active_field = "h"
					else:
						settings_active_field = None
						
			fps_options = [30, 60, 120, 144]
			for i, rect in enumerate(fps_rects):
				if rect.collidepoint(mouse_x, mouse_y):
					settings_fps = fps_options[i]
					
			for i, rect in enumerate(scale_rects):
				if rect.collidepoint(mouse_x, mouse_y):
					settings_scale_str = settings_ui_scale_opts[i]
					
			if apply_rect.collidepoint(mouse_x, mouse_y):
				TARGET_FPS = settings_fps
				FRAME_MS = 1000 / TARGET_FPS
				
				w, h = window_w, window_h
				new_fullscreen = fullscreen
				if settings_fullscreen:
					w, h = 0, 0
					new_fullscreen = True
				else:
					new_fullscreen = False
					if settings_selected_preset >= 0:
						w, h = settings_presets[settings_selected_preset]
					else:
						try:
							w = int(settings_custom_w)
							h = int(settings_custom_h)
						except ValueError:
							w, h = window_w, window_h
				
				if w != 0 and h != 0:
					w = max(MIN_WIDTH, w)
					h = max(MIN_HEIGHT, h)
				
				apply_display_settings(new_fullscreen, w, h, settings_scale_str)
				queue_save()
				game_state = "menu"
				
			if back_rect.collidepoint(mouse_x, mouse_y):
				game_state = "menu"

		if e.type == pygame.KEYDOWN:
			if e.key == pygame.K_BACKQUOTE:
				console_open = not console_open
				console_input = ""
				continue

			if console_open:
				if e.key == pygame.K_ESCAPE:
					console_open = False
					console_input = ""
				elif e.key == pygame.K_RETURN:
					result = console_exec(console_input)
					if result:
						console_log.append((f"$ {console_input}", CONSOLE_CMD))
						console_log.append(result)
					console_input = ""
				elif e.key == pygame.K_BACKSPACE:
					console_input = console_input[:-1]
				elif e.unicode and e.unicode.isprintable():
					console_input += e.unicode
				continue

			if game_state == "menu":
				if e.key == pygame.K_SPACE:
					reset_run()
				if e.key == pygame.K_s:
					game_state = "shop"
				if e.key == pygame.K_o:
					game_state = "settings"
					settings_fullscreen = fullscreen
					settings_selected_preset = -1
					for i, p in enumerate(settings_presets):
						if p == (window_w, window_h):
							settings_selected_preset = i
					settings_custom_w = str(window_w)
					settings_custom_h = str(window_h)
					settings_active_field = None
					settings_fps = TARGET_FPS
					settings_scale_str = ui_scale_str
				if e.key == pygame.K_q:
					save_game()
					sys.exit()

			elif game_state == "settings":
				if settings_active_field == "w":
					if e.key == pygame.K_BACKSPACE:
						settings_custom_w = settings_custom_w[:-1]
					elif e.unicode.isdigit() and len(settings_custom_w) < 4:
						settings_custom_w += e.unicode
					elif e.key == pygame.K_TAB:
						settings_active_field = "h"
				elif settings_active_field == "h":
					if e.key == pygame.K_BACKSPACE:
						settings_custom_h = settings_custom_h[:-1]
					elif e.unicode.isdigit() and len(settings_custom_h) < 4:
						settings_custom_h += e.unicode
					elif e.key == pygame.K_TAB:
						settings_active_field = "w"
				
				if e.key == pygame.K_ESCAPE:
					game_state = "menu"

			elif game_state == "shop":
				if e.key == pygame.K_1 and coins >= 20:
					player_speed += 1
					coins -= 20
					queue_save()
				if e.key == pygame.K_2 and coins >= 30:
					jump_strength -= 2
					coins -= 30
					queue_save()
				if e.key == pygame.K_3 and coins >= 100:
					shield_cooldown_real = max(120, shield_cooldown_real - 10)
					shield_time_real += 10
					coins -= 100
					queue_save()
				if e.key == pygame.K_4 and coins >= 150:
					magnet_level += 1
					coins -= 150
					queue_save()
				if e.key == pygame.K_ESCAPE:
					game_state = "menu"

			elif game_state == "pause":
				if e.key == pygame.K_ESCAPE:
					game_state = "game"
				if e.key == pygame.K_m:
					game_state = "menu"
				if e.key == pygame.K_q:
					save_game()
					pygame.quit()
					sys.exit()

			elif game_state == "gameover":
				if tick >= gameover_input_unlock_at:
					if e.key == pygame.K_SPACE:
						reset_run()
					if e.key == pygame.K_m:
						game_state = "menu"
					if e.key == pygame.K_s:
						game_state = "shop"
					if e.key == pygame.K_q:
						save_game()
						sys.exit()

			elif game_state == "game":
				if e.key == pygame.K_SPACE:
					jump_buffer_time = jump_buffer_max
				if e.key == pygame.K_q and dash_cooldown <= 0:
					dash_velocity = DASH_SPEED * facing
					dash_duration = 12
					dash_cooldown = 60
				if e.key == pygame.K_e and shield_cooldown <= 0:
					shield = True
					shield_time = shield_time_real
					shield_cooldown = shield_cooldown_real
				if e.key == pygame.K_ESCAPE:
					game_state = "pause"

		if e.type == pygame.KEYUP and game_state == "game":
			if console_open:
				continue
			if e.key == pygame.K_SPACE:
				jump_hold_time = 0

	# ---------- GAME ----------
	if game_state == "game" and not console_open:
		keys = pygame.key.get_pressed()
		on_ground = player.bottom >= HEIGHT - GROUND_OFFSET

		# facing and movement
		move_dir = 0
		if keys[pygame.K_a] or keys[pygame.K_LEFT]:
			move_dir -= 1
		if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
			move_dir += 1

		run_max_speed = player_speed
		if move_dir != 0:
			facing = move_dir
			player_vx += move_dir * run_accel * dt
		else:
			player_vx *= run_friction ** dt

		player_vx = clamp(player_vx, -run_max_speed, run_max_speed)
		player_pos_x += player_vx * dt
		player.x = int(player_pos_x)

		if player.x < 0:
			player.x = 0
			player_pos_x = float(player.x)
			player_vx = 0
		if player.right > WIDTH:
			player.right = WIDTH
			player_pos_x = float(player.x)
			player_vx = 0

		# variable jump: hold SPACE for a little extra lift
		if keys[pygame.K_SPACE] and jump_hold_time > 0 and velocity_y < 0:
			velocity_y -= 0.75 * dt
			jump_hold_time = update_timer(jump_hold_time, dt)

		if jump_buffer_time > 0:
			jump_buffer_time = update_timer(jump_buffer_time, dt)
			if on_ground or coyote_time > 0 or jumps_left > 0:
				velocity_y = jump_strength
				if on_ground or coyote_time > 0:
					jumps_left = max(0, jumps_left - 1)
				else:
					jumps_left -= 1
				jump_hold_time = jump_hold_max
				jump_buffer_time = 0

		velocity_y += gravity * dt
		player_pos_y += velocity_y * dt
		player.y = int(player_pos_y)

		if player.bottom >= HEIGHT - GROUND_OFFSET:
			player.bottom = HEIGHT - GROUND_OFFSET
			player_pos_y = float(player.y)
			velocity_y = 0
			jumps_left = max_jumps
			jump_hold_time = 0
			coyote_time = coyote_max
		else:
			coyote_time = update_timer(coyote_time, dt)

		# dash with wall bounce
		if dash_duration > 0:
			dash_velocity *= 0.95 ** dt
			player_pos_x += dash_velocity * dt
			player.x = int(player_pos_x)
			dash_duration = update_timer(dash_duration, dt)

			hit_wall = False
			if player.left <= 0:
				player.left = 0
				player_pos_x = float(player.x)
				hit_wall = True
			elif player.right >= WIDTH:
				player.right = WIDTH
				player_pos_x = float(player.x)
				hit_wall = True

			if hit_wall:
				dash_velocity *= -0.65
				dash_duration = max(0, dash_duration - 2)
				facing = 1 if dash_velocity >= 0 else -1
				dash_trail.append(
					{
						"rect": player.copy(),
						"life": 12,
						"color": (120, 210, 255),
					}
				)

		if dash_cooldown > 0:
			dash_cooldown = update_timer(dash_cooldown, dt)

		# shield
		if shield:
			shield_time = update_timer(shield_time, dt)
			shield_flash = 10
			if shield_time <= 0:
				shield = False
		if shield_cooldown > 0:
			shield_cooldown = update_timer(shield_cooldown, dt)
		if shield_flash > 0:
			shield_flash = update_timer(shield_flash, dt)

		# spawn
		if tick >= next_magma_spawn:
			spawn_magma_pattern()
			next_magma_spawn = tick + random.randint(380, 700)

		if tick >= next_coin_spawn:
			spawn_coin_pattern()
			next_coin_spawn = tick + random.randint(850, 1350)

		# magma speed ramps with score
		magma_speed = min(MAGMA_MAX_SPEED, MAGMA_BASE_SPEED + score * MAGMA_SCORE_SCALE)

		# magma
		magma_to_remove = []
		for m in magma_list:
			m.y += int(round(magma_speed * dt))
			if m.colliderect(player):
				if shield:
					magma_to_remove.append(m)
					shield_flash = max(shield_flash, 14)
				else:
					coins += score
					queue_save()
					game_state = "gameover"
					gameover_input_unlock_at = tick + 180
					break
			elif m.top > HEIGHT:
				magma_to_remove.append(m)
				score += 1
		if magma_to_remove:
			removed_ids = {id(m) for m in magma_to_remove}
			magma_list = [m for m in magma_list if id(m) not in removed_ids]

		# coin
		collected_coins = 0
		next_coin_list = []
		magnet_radius = 150 + magnet_level * 50
		magnet_speed = 10 + magnet_level * 3
		for c in coin_list:
			if magnet_level > 0:
				dx = player.centerx - c.centerx
				dy = player.centery - c.centery
				dist = math.hypot(dx, dy)
				if dist < magnet_radius and dist > 0:
					c.x += (dx / dist) * magnet_speed * dt
					c.y += (dy / dist) * magnet_speed * dt
				else:
					c.y += int(round(COIN_FALL_SPEED * dt))
			else:
				c.y += int(round(COIN_FALL_SPEED * dt))

			if c.colliderect(player):
				collected_coins += 1
			elif c.top > HEIGHT:
				continue
			else:
				next_coin_list.append(c)
		if collected_coins:
			coins += collected_coins
			queue_save()
		coin_list = next_coin_list

		# trail particles
		next_dash_trail = []
		for p in dash_trail:
			p["life"] = update_timer(p["life"], dt)
			if p["life"] > 0:
				next_dash_trail.append(p)
		dash_trail = next_dash_trail

		# draw trail
		for p in dash_trail:
			rect = p["rect"]
			alpha = int(20 + p["life"] * 8)
			glow = get_trail_surface((rect.width, rect.height), alpha)
			screen.blit(glow, (rect.x - 15, rect.y - 15))

		# draw world
		for m in magma_list:
			draw_magma(m)

		for c in coin_list:
			draw_coin(c, tick)

		draw_player()

		if shield:
			pulse = 28 + int((math.sin(tick * 0.03) + 1) * 2)
			draw_glow_circle(player.center, pulse, GREEN, 75)
			pygame.draw.circle(screen, GREEN, player.center, pulse, 3)
		elif shield_flash > 0:
			draw_glow_circle(player.center, 28 + shield_flash, BLUE, 60)

		draw_hud()
		draw_ability_bar()

	elif game_state == "menu":
		draw_menu()
		draw_info_hub()

	elif game_state == "settings":
		draw_settings()
		draw_info_hub()

	elif game_state == "shop":
		draw_shop()
		draw_info_hub()

	elif game_state == "pause":
		draw_pause()
		draw_info_hub()

	elif game_state == "gameover":
		draw_gameover()
		draw_info_hub()

	if console_open:
		draw_console()

	if WIDTH == window_w and HEIGHT == window_h:
		display_screen.blit(screen, (0, 0))
	else:
		scaled_screen = pygame.transform.scale(screen, display_screen.get_size())
		display_screen.blit(scaled_screen, (0, 0))
	pygame.display.flip()