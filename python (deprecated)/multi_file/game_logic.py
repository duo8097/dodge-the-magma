import random
import pygame

import py_version.many_file_ver.game_state as gs
from py_version.many_file_ver.constants import (
	GROUND_OFFSET, MAGMA_SIZE, COIN_SIZE,
)
from py_version.many_file_ver.helpers import clamp


def update_timer(value, amount):
	return max(0.0, value - amount)


def reset_run():
	gs.score = 0
	gs.game_state = "game"
	gs.gameover_input_unlock_at = 0
	gs.player.x = gs.WIDTH // 2
	gs.player.bottom = gs.HEIGHT - GROUND_OFFSET
	gs.player_pos_x = float(gs.player.x)
	gs.player_pos_y = float(gs.player.y)
	gs.velocity_y = 0.0
	gs.player_vx = 0.0
	gs.jumps_left = gs.max_jumps
	gs.jump_hold_time = 0
	gs.coyote_time = 0
	gs.jump_buffer_time = 0
	gs.dash_velocity = 0.0
	gs.dash_duration = 0
	gs.dash_cooldown = 0
	gs.dash_trail = []
	gs.shield = False
	gs.shield_time = 0
	gs.shield_cooldown = 0
	gs.shield_flash = 0
	gs.magma_list.clear()
	gs.coin_list.clear()
	gs.facing = 1
	now = pygame.time.get_ticks()
	gs.next_magma_spawn = now + 300
	gs.next_coin_spawn = now + 900


def spawn_magma_pattern():
	pattern = random.choices(
		["single", "double", "cluster", "zigzag"],
		weights=[45, 20, 25, 10],
		k=1,
	)[0]
	spawn_x = random.randint(20, max(20, gs.WIDTH - 50))
	pieces = []

	if pattern == "single":
		pieces.append(pygame.Rect(spawn_x, -30, 30, 30))
	elif pattern == "double":
		offset = random.choice([40, 55])
		pieces.append(pygame.Rect(clamp(spawn_x, 0, gs.WIDTH - MAGMA_SIZE), -MAGMA_SIZE, MAGMA_SIZE, MAGMA_SIZE))
		pieces.append(
			pygame.Rect(clamp(spawn_x + offset, 0, gs.WIDTH - MAGMA_SIZE), -MAGMA_SIZE, MAGMA_SIZE, MAGMA_SIZE)
		)
	elif pattern == "cluster":
		offsets = [-44, -12, 20, 52]
		for off in random.sample(offsets, k=random.randint(3, 4)):
			pieces.append(
				pygame.Rect(clamp(spawn_x + off, 0, gs.WIDTH - MAGMA_SIZE), -MAGMA_SIZE, MAGMA_SIZE, MAGMA_SIZE)
			)
	else:
		lane = random.randint(0, 3)
		for i in range(4):
			x = clamp(spawn_x + (i - lane) * 34, 0, gs.WIDTH - MAGMA_SIZE)
			pieces.append(pygame.Rect(x, -MAGMA_SIZE - i * 10, MAGMA_SIZE, MAGMA_SIZE))

	gs.magma_list.extend(pieces)


def spawn_coin_pattern():
	pattern = random.choices(
		["single", "zigzag", "line", "reward"],
		weights=[42, 28, 20, 10],
		k=1,
	)[0]
	base_x = random.randint(15, max(15, gs.WIDTH - 35))
	base_y = -20
	coins_to_add = []

	if pattern == "single":
		coins_to_add.append(pygame.Rect(base_x, base_y, COIN_SIZE, COIN_SIZE))
	elif pattern == "zigzag":
		for i in range(5):
			x = clamp(base_x + (-1) ** i * (18 + i * 2), 0, gs.WIDTH - COIN_SIZE)
			y = base_y - i * 22
			coins_to_add.append(pygame.Rect(x, y, COIN_SIZE, COIN_SIZE))
	elif pattern == "line":
		for i in range(4):
			x = clamp(base_x + i * 26, 0, gs.WIDTH - COIN_SIZE)
			coins_to_add.append(pygame.Rect(x, base_y - i * 8, COIN_SIZE, COIN_SIZE))
	else:
		for i in range(3):
			x = clamp(base_x + i * 34 - 34, 0, gs.WIDTH - COIN_SIZE)
			y = base_y - abs(i - 1) * 18
			coins_to_add.append(pygame.Rect(x, y, COIN_SIZE, COIN_SIZE))

	gs.coin_list.extend(coins_to_add)
