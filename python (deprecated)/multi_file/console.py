import sys
import pygame

import py_version.many_file_ver.game_state as gs
from py_version.many_file_ver.constants import (
	CONSOLE_BG, CONSOLE_CMD, CONSOLE_OK, CONSOLE_ERR, CONSOLE_INFO,
)
from py_version.many_file_ver.save_manager import save_game, queue_save


def console_exec(cmd):
	parts = cmd.strip().lower().split()
	if not parts:
		return None

	command = parts[0]
	arg = parts[1] if len(parts) > 1 else None

	if command == "coin":
		amount = int(arg) if arg and arg.isdigit() else 100
		gs.coins += amount
		queue_save()
		return (f"+{amount} coins", CONSOLE_OK)

	if command == "speed":
		amount = int(arg) if arg and arg.isdigit() else 2
		gs.player_speed += amount
		queue_save()
		return (f"speed -> {gs.player_speed}", CONSOLE_OK)

	if command == "jump":
		amount = int(arg) if arg and arg.isdigit() else 2
		gs.jump_strength -= amount
		queue_save()
		return (f"jump -> {gs.jump_strength}", CONSOLE_OK)

	if command == "god":
		gs.shield = True
		gs.shield_time = 999999
		return ("god mode ON", CONSOLE_OK)

	if command == "reset":
		if arg == "jump":
			gs.jump_strength = -22
			queue_save()
			return ("jump reset", CONSOLE_OK)
		if arg == "coin":
			gs.coins = 0
			queue_save()
			return ("coins reset", CONSOLE_OK)
		if arg == "speed":
			gs.player_speed = 8
			queue_save()
			return ("speed reset", CONSOLE_OK)
		if arg == "shield":
			gs.shield_cooldown_real = 300
			gs.shield_time_real = 120
			queue_save()
			return ("shield reset", CONSOLE_OK)
		if arg == "all" or arg is None:
			gs.coins = 0
			gs.player_speed = 8
			gs.shield_cooldown_real = 300
			gs.shield_time_real = 120
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
		return (f"coins: {gs.coins}, speed: {gs.player_speed}, jump: {gs.jump_strength}, shield_cd: {gs.shield_cooldown_real}, shield_time: {gs.shield_time_real}", CONSOLE_INFO)

	return (f"unknown: {command}", CONSOLE_ERR)


def draw_console():
	h = 180
	y0 = gs.HEIGHT - h
	overlay = pygame.Surface((gs.WIDTH, h), pygame.SRCALPHA)
	overlay.fill(CONSOLE_BG)
	gs.screen.blit(overlay, (0, y0))
	pygame.draw.line(gs.screen, (60, 60, 120), (0, y0), (gs.WIDTH, y0), 1)

	header = gs.small_font.render("CHEAT CONSOLE  [ ESC close ]", True, CONSOLE_INFO)
	gs.screen.blit(header, (14, y0 + 8))

	line_h = 22
	input_y = gs.HEIGHT - 30
	max_display_lines = (input_y - 4 - (y0 + 32)) // line_h

	visible_logs = gs.console_log[-max_display_lines:]

	start_y = input_y - 4 - len(visible_logs) * line_h
	for i, (text, color) in enumerate(visible_logs):
		line_surface = gs.small_font.render(text, True, color)
		gs.screen.blit(line_surface, (14, start_y + i * line_h))

	pygame.draw.line(gs.screen, (60, 60, 120), (0, input_y - 4), (gs.WIDTH, input_y - 4), 1)
	prompt = gs.small_font.render("$ " + gs.console_input, True, CONSOLE_CMD)
	gs.screen.blit(prompt, (14, input_y))

	if (pygame.time.get_ticks() // 500) % 2 == 0:
		cursor_x = 14 + prompt.get_width() + 2
		pygame.draw.rect(gs.screen, CONSOLE_CMD, (cursor_x, input_y + 2, 2, 18))
