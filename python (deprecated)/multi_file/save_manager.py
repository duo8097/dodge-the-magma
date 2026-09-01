import os
import json
import pygame

import py_version.many_file_ver.game_state as gs


def save_game():
	data = {
		"coins": gs.coins,
		"player_speed": gs.player_speed,
		"jump_strength": gs.jump_strength,
		"shield_cooldown_real": gs.shield_cooldown_real,
		"shield_time_real": gs.shield_time_real,
		"magnet_level": gs.magnet_level,
		"target_fps": gs.target_fps,
		"ui_scale_str": gs.ui_scale_str,
	}
	temp_file = "save.json.tmp"
	with open(temp_file, "w") as f:
		json.dump(data, f)
		f.flush()
		os.fsync(f.fileno())
	os.replace(temp_file, "save.json")
	gs.save_dirty = False
	gs.last_save_tick = pygame.time.get_ticks()


def queue_save():
	gs.save_dirty = True


def load_game():
	try:
		with open("save.json", "r") as f:
			data = json.load(f)
			gs.coins = data.get("coins", gs.coins)
			gs.player_speed = data.get("player_speed", gs.player_speed)
			gs.jump_strength = data.get("jump_strength", gs.jump_strength)
			gs.shield_cooldown_real = data.get(
				"shield_cooldown_real", gs.shield_cooldown_real
			)
			gs.shield_time_real = data.get("shield_time_real", gs.shield_time_real)
			gs.magnet_level = data.get("magnet_level", gs.magnet_level)
			gs.target_fps = data.get("target_fps", gs.target_fps)
			gs.frame_ms = 1000 / gs.target_fps
			gs.ui_scale_str = data.get("ui_scale_str", gs.ui_scale_str)
	except Exception:
		save_game()
