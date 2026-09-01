import pygame
from py_version.many_file_ver.constants import PLAYER_SIZE, DEFAULT_WIDTH, DEFAULT_HEIGHT, TARGET_FPS

WIDTH = DEFAULT_WIDTH
HEIGHT = DEFAULT_HEIGHT

target_fps = TARGET_FPS
frame_ms = 1000 / target_fps

coins = 0
player_speed = 8
jump_strength = -22
shield_cooldown_real = 300
shield_time_real = 120
magnet_level = 0
save_dirty = False
last_save_tick = 0
magma_glow_surface = None
ui_scale_str = "Auto"

clock = None
font = None
small_font = None
big_font = None
screen = None
display_screen = None
fullscreen = False
window_w = DEFAULT_WIDTH
window_h = DEFAULT_HEIGHT


def init_fonts():
	global clock, font, small_font, big_font
	clock = pygame.time.Clock()
	font = pygame.font.SysFont("Consolas", 28)
	small_font = pygame.font.SysFont("Consolas", 22)
	big_font = pygame.font.SysFont("Consolas", 48)


player = None
player_pos_x = 0.0
player_pos_y = 0.0
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

dash_velocity = 0.0
dash_duration = 0
dash_cooldown = 0
dash_trail = []
dash_trail_timer = 0

shield = False
shield_time = 0
shield_cooldown = 0
shield_flash = 0

magma_list = []
coin_list = []
next_magma_spawn = 0
next_coin_spawn = 0

score = 0
game_state = "menu"
gameover_input_unlock_at = 0
console_open = False
console_input = ""
console_log = []

settings_presets = [(1280, 720), (1600, 900), (1920, 1080)]
settings_selected_preset = -1
settings_custom_w = "1280"
settings_custom_h = "720"
settings_active_field = None
settings_fullscreen = False
settings_fps = target_fps
settings_ui_scale_opts = ["Auto", "100%", "125%", "150%", "175%", "200%"]
settings_scale_str = "Auto"


def init_player():
	global player, player_pos_x, player_pos_y, velocity_y, player_vx
	global jumps_left, facing, next_magma_spawn, next_coin_spawn
	player = pygame.Rect(WIDTH // 2, HEIGHT - 100, PLAYER_SIZE, PLAYER_SIZE)
	player_pos_x = float(player.x)
	player_pos_y = float(player.y)
	velocity_y = 0.0
	player_vx = 0.0
	jumps_left = max_jumps
	facing = 1
	now = pygame.time.get_ticks()
	next_magma_spawn = now + 300
	next_coin_spawn = now + 900
