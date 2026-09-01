import ctypes
import math
import pygame
import random
import sys

import py_version.many_file_ver.game_state as gs
from py_version.many_file_ver.constants import (
	IS_WINDOWS, GROUND_OFFSET, DASH_SPEED, COIN_FALL_SPEED,
	MIN_WIDTH, MIN_HEIGHT,
	BLUE, GREEN, YELLOW, RED, BG, GRID,
	CONSOLE_CMD, MAGMA_BASE_SPEED, MAGMA_MAX_SPEED, MAGMA_SCORE_SCALE,
)
from py_version.many_file_ver.save_manager import save_game, queue_save, load_game
from py_version.many_file_ver.display import apply_display_settings, run_startup_screen
from py_version.many_file_ver.helpers import clamp, draw_glow_circle, get_trail_surface
from py_version.many_file_ver.game_logic import (
	update_timer, reset_run, spawn_magma_pattern, spawn_coin_pattern,
)
from py_version.many_file_ver.renderer import draw_player, draw_magma, draw_coin
from py_version.many_file_ver.console import console_exec, draw_console
from py_version.many_file_ver.ui import (
	draw_hud, draw_ability_bar, draw_info_hub, draw_menu,
	draw_settings, draw_shop, draw_pause, draw_gameover, get_settings_rects,
)


def main():
	if IS_WINDOWS:
		ctypes.windll.user32.SetProcessDPIAware()
	pygame.init()

	gs.init_fonts()

	startup_screen = pygame.display.set_mode((560, 380))
	pygame.display.set_caption("DODGE THE MAGMA")
	start_w, start_h, fullscreen = run_startup_screen(startup_screen)

	pygame.quit()
	pygame.init()
	gs.init_fonts()

	load_game()

	display_info = pygame.display.Info()
	init_w = max(MIN_WIDTH, min(start_w, display_info.current_w - 120))
	init_h = max(MIN_HEIGHT, min(start_h, display_info.current_h - 120))
	gs.display_screen = None
	apply_display_settings(fullscreen, init_w, init_h, gs.ui_scale_str)

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

	gs.init_player()

	while True:
		dt = gs.clock.tick(gs.target_fps) / gs.frame_ms
		tick = pygame.time.get_ticks()

		gs.screen.fill(BG)
		for x in range(0, gs.WIDTH, 40):
			pygame.draw.line(gs.screen, GRID, (x, 0), (x, gs.HEIGHT))
		for y in range(0, gs.HEIGHT, 40):
			pygame.draw.line(gs.screen, GRID, (0, y), (gs.WIDTH, y))

		if gs.save_dirty and tick - gs.last_save_tick >= 5000:
			save_game()

		for e in pygame.event.get():
			if e.type == pygame.QUIT:
				save_game()
				pygame.quit()
				sys.exit()

			if e.type == pygame.MOUSEBUTTONDOWN and gs.game_state == "settings":
				mouse_x, mouse_y = e.pos
				scale_x = gs.WIDTH / gs.window_w
				scale_y = gs.HEIGHT / gs.window_h
				mouse_x = int(mouse_x * scale_x)
				mouse_y = int(mouse_y * scale_y)
				btn_window, btn_full, preset_rects, custom_rect, width_rect, height_rect, apply_rect, back_rect, fps_rects, scale_rects = get_settings_rects()

				if btn_window.collidepoint(mouse_x, mouse_y):
					gs.settings_fullscreen = False
				if btn_full.collidepoint(mouse_x, mouse_y):
					gs.settings_fullscreen = True
					gs.settings_active_field = None
				if not gs.settings_fullscreen:
					for i, rect in enumerate(preset_rects):
						if rect.collidepoint(mouse_x, mouse_y):
							gs.settings_selected_preset = i
							gs.settings_active_field = None
					if custom_rect.collidepoint(mouse_x, mouse_y):
						gs.settings_selected_preset = -1
					if gs.settings_selected_preset == -1:
						if width_rect and width_rect.collidepoint(mouse_x, mouse_y):
							gs.settings_active_field = "w"
						elif height_rect and height_rect.collidepoint(mouse_x, mouse_y):
							gs.settings_active_field = "h"
						else:
							gs.settings_active_field = None

				fps_options = [30, 60, 120, 144]
				for i, rect in enumerate(fps_rects):
					if rect.collidepoint(mouse_x, mouse_y):
						gs.settings_fps = fps_options[i]

				for i, rect in enumerate(scale_rects):
					if rect.collidepoint(mouse_x, mouse_y):
						gs.settings_scale_str = gs.settings_ui_scale_opts[i]

				if apply_rect.collidepoint(mouse_x, mouse_y):
					gs.target_fps = gs.settings_fps
					gs.frame_ms = 1000 / gs.target_fps

					w, h = gs.window_w, gs.window_h
					new_fullscreen = gs.fullscreen
					if gs.settings_fullscreen:
						w, h = 0, 0
						new_fullscreen = True
					else:
						new_fullscreen = False
						if gs.settings_selected_preset >= 0:
							w, h = gs.settings_presets[gs.settings_selected_preset]
						else:
							try:
								w = int(gs.settings_custom_w)
								h = int(gs.settings_custom_h)
							except ValueError:
								w, h = gs.window_w, gs.window_h

					if w != 0 and h != 0:
						w = max(MIN_WIDTH, w)
						h = max(MIN_HEIGHT, h)

					apply_display_settings(new_fullscreen, w, h, gs.settings_scale_str)
					queue_save()
					gs.game_state = "menu"

				if back_rect.collidepoint(mouse_x, mouse_y):
					gs.game_state = "menu"

			if e.type == pygame.KEYDOWN:
				if e.key == pygame.K_BACKQUOTE:
					gs.console_open = not gs.console_open
					gs.console_input = ""
					continue

				if gs.console_open:
					if e.key == pygame.K_ESCAPE:
						gs.console_open = False
						gs.console_input = ""
					elif e.key == pygame.K_RETURN:
						result = console_exec(gs.console_input)
						if result:
							gs.console_log.append((f"$ {gs.console_input}", CONSOLE_CMD))
							gs.console_log.append(result)
						gs.console_input = ""
					elif e.key == pygame.K_BACKSPACE:
						gs.console_input = gs.console_input[:-1]
					elif e.unicode and e.unicode.isprintable():
						gs.console_input += e.unicode
					continue

				if gs.game_state == "menu":
					if e.key == pygame.K_SPACE:
						reset_run()
					if e.key == pygame.K_s:
						gs.game_state = "shop"
					if e.key == pygame.K_o:
						gs.game_state = "settings"
						gs.settings_fullscreen = gs.fullscreen
						gs.settings_selected_preset = -1
						for i, p in enumerate(gs.settings_presets):
							if p == (gs.window_w, gs.window_h):
								gs.settings_selected_preset = i
						gs.settings_custom_w = str(gs.window_w)
						gs.settings_custom_h = str(gs.window_h)
						gs.settings_active_field = None
						gs.settings_fps = gs.target_fps
						gs.settings_scale_str = gs.ui_scale_str
					if e.key == pygame.K_q:
						save_game()
						sys.exit()

				elif gs.game_state == "settings":
					if gs.settings_active_field == "w":
						if e.key == pygame.K_BACKSPACE:
							gs.settings_custom_w = gs.settings_custom_w[:-1]
						elif e.unicode.isdigit() and len(gs.settings_custom_w) < 4:
							gs.settings_custom_w += e.unicode
						elif e.key == pygame.K_TAB:
							gs.settings_active_field = "h"
					elif gs.settings_active_field == "h":
						if e.key == pygame.K_BACKSPACE:
							gs.settings_custom_h = gs.settings_custom_h[:-1]
						elif e.unicode.isdigit() and len(gs.settings_custom_h) < 4:
							gs.settings_custom_h += e.unicode
						elif e.key == pygame.K_TAB:
							gs.settings_active_field = "w"

					if e.key == pygame.K_ESCAPE:
						gs.game_state = "menu"

				elif gs.game_state == "shop":
					if e.key == pygame.K_1 and gs.coins >= 20:
						gs.player_speed += 1
						gs.coins -= 20
						queue_save()
					if e.key == pygame.K_2 and gs.coins >= 30:
						gs.jump_strength -= 2
						gs.coins -= 30
						queue_save()
					if e.key == pygame.K_3 and gs.coins >= 100:
						gs.shield_cooldown_real = max(120, gs.shield_cooldown_real - 10)
						gs.shield_time_real += 10
						gs.coins -= 100
						queue_save()
					if e.key == pygame.K_4 and gs.coins >= 150:
						gs.magnet_level += 1
						gs.coins -= 150
						queue_save()
					if e.key == pygame.K_ESCAPE:
						gs.game_state = "menu"

				elif gs.game_state == "pause":
					if e.key == pygame.K_ESCAPE:
						gs.game_state = "game"
					if e.key == pygame.K_m:
						gs.game_state = "menu"
					if e.key == pygame.K_q:
						save_game()
						pygame.quit()
						sys.exit()

				elif gs.game_state == "gameover":
					if tick >= gs.gameover_input_unlock_at:
						if e.key == pygame.K_SPACE:
							reset_run()
						if e.key == pygame.K_m:
							gs.game_state = "menu"
						if e.key == pygame.K_s:
							gs.game_state = "shop"
						if e.key == pygame.K_q:
							save_game()
							sys.exit()

				elif gs.game_state == "game":
					if e.key == pygame.K_SPACE:
						gs.jump_buffer_time = gs.jump_buffer_max
					if e.key == pygame.K_q and gs.dash_cooldown <= 0:
						gs.dash_velocity = DASH_SPEED * gs.facing
						gs.dash_duration = 12
						gs.dash_cooldown = 60
					if e.key == pygame.K_e and gs.shield_cooldown <= 0:
						gs.shield = True
						gs.shield_time = gs.shield_time_real
						gs.shield_cooldown = gs.shield_cooldown_real
					if e.key == pygame.K_ESCAPE:
						gs.game_state = "pause"

			if e.type == pygame.KEYUP and gs.game_state == "game":
				if gs.console_open:
					continue
				if e.key == pygame.K_SPACE:
					gs.jump_hold_time = 0

		if gs.game_state == "game" and not gs.console_open:
			keys = pygame.key.get_pressed()
			on_ground = gs.player.bottom >= gs.HEIGHT - GROUND_OFFSET

			move_dir = 0
			if keys[pygame.K_a] or keys[pygame.K_LEFT]:
				move_dir -= 1
			if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
				move_dir += 1

			gs.run_max_speed = gs.player_speed
			if move_dir != 0:
				gs.facing = move_dir
				gs.player_vx += move_dir * gs.run_accel * dt
			else:
				gs.player_vx *= gs.run_friction ** dt

			gs.player_vx = clamp(gs.player_vx, -gs.run_max_speed, gs.run_max_speed)
			gs.player_pos_x += gs.player_vx * dt
			gs.player.x = int(gs.player_pos_x)

			if gs.player.x < 0:
				gs.player.x = 0
				gs.player_pos_x = float(gs.player.x)
				gs.player_vx = 0
			if gs.player.right > gs.WIDTH:
				gs.player.right = gs.WIDTH
				gs.player_pos_x = float(gs.player.x)
				gs.player_vx = 0

			if keys[pygame.K_SPACE] and gs.jump_hold_time > 0 and gs.velocity_y < 0:
				gs.velocity_y -= 0.75 * dt
				gs.jump_hold_time = update_timer(gs.jump_hold_time, dt)

			if gs.jump_buffer_time > 0:
				gs.jump_buffer_time = update_timer(gs.jump_buffer_time, dt)
				if on_ground or gs.coyote_time > 0 or gs.jumps_left > 0:
					gs.velocity_y = gs.jump_strength
					if on_ground or gs.coyote_time > 0:
						gs.jumps_left = max(0, gs.jumps_left - 1)
					else:
						gs.jumps_left -= 1
					gs.jump_hold_time = gs.jump_hold_max
					gs.jump_buffer_time = 0

			gs.velocity_y += gs.gravity * dt
			gs.player_pos_y += gs.velocity_y * dt
			gs.player.y = int(gs.player_pos_y)

			if gs.player.bottom >= gs.HEIGHT - GROUND_OFFSET:
				gs.player.bottom = gs.HEIGHT - GROUND_OFFSET
				gs.player_pos_y = float(gs.player.y)
				gs.velocity_y = 0
				gs.jumps_left = gs.max_jumps
				gs.jump_hold_time = 0
				gs.coyote_time = gs.coyote_max
			else:
				gs.coyote_time = update_timer(gs.coyote_time, dt)

			if gs.dash_duration > 0:
				gs.dash_velocity *= 0.95 ** dt
				gs.player_pos_x += gs.dash_velocity * dt
				gs.player.x = int(gs.player_pos_x)
				gs.dash_duration = update_timer(gs.dash_duration, dt)

				hit_wall = False
				if gs.player.left <= 0:
					gs.player.left = 0
					gs.player_pos_x = float(gs.player.x)
					hit_wall = True
				elif gs.player.right >= gs.WIDTH:
					gs.player.right = gs.WIDTH
					gs.player_pos_x = float(gs.player.x)
					hit_wall = True

				if hit_wall:
					gs.dash_velocity *= -0.65
					gs.dash_duration = max(0, gs.dash_duration - 2)
					gs.facing = 1 if gs.dash_velocity >= 0 else -1
					gs.dash_trail.append(
						{
							"rect": gs.player.copy(),
							"life": 12,
							"color": (120, 210, 255),
						}
					)

			if gs.dash_cooldown > 0:
				gs.dash_cooldown = update_timer(gs.dash_cooldown, dt)

			if gs.shield:
				gs.shield_time = update_timer(gs.shield_time, dt)
				gs.shield_flash = 10
				if gs.shield_time <= 0:
					gs.shield = False
			if gs.shield_cooldown > 0:
				gs.shield_cooldown = update_timer(gs.shield_cooldown, dt)
			if gs.shield_flash > 0:
				gs.shield_flash = update_timer(gs.shield_flash, dt)

			if tick >= gs.next_magma_spawn:
				spawn_magma_pattern()
				gs.next_magma_spawn = tick + random.randint(380, 700)

			if tick >= gs.next_coin_spawn:
				spawn_coin_pattern()
				gs.next_coin_spawn = tick + random.randint(850, 1350)

			magma_speed = min(MAGMA_MAX_SPEED, MAGMA_BASE_SPEED + gs.score * MAGMA_SCORE_SCALE)

			magma_to_remove = []
			for m in gs.magma_list:
				m.y += int(round(magma_speed * dt))
				if m.colliderect(gs.player):
					if gs.shield:
						magma_to_remove.append(m)
						gs.shield_flash = max(gs.shield_flash, 14)
					else:
						gs.coins += gs.score
						queue_save()
						gs.game_state = "gameover"
						gs.gameover_input_unlock_at = tick + 180
						break
				elif m.top > gs.HEIGHT:
					magma_to_remove.append(m)
					gs.score += 1
			if magma_to_remove:
				removed_ids = {id(m) for m in magma_to_remove}
				gs.magma_list = [m for m in gs.magma_list if id(m) not in removed_ids]

			collected_coins = 0
			next_coin_list = []
			magnet_radius = 150 + gs.magnet_level * 50
			magnet_speed = 10 + gs.magnet_level * 3
			for c in gs.coin_list:
				if gs.magnet_level > 0:
					dx = gs.player.centerx - c.centerx
					dy = gs.player.centery - c.centery
					dist = math.hypot(dx, dy)
					if dist < magnet_radius and dist > 0:
						c.x += (dx / dist) * magnet_speed * dt
						c.y += (dy / dist) * magnet_speed * dt
					else:
						c.y += int(round(COIN_FALL_SPEED * dt))
				else:
					c.y += int(round(COIN_FALL_SPEED * dt))

				if c.colliderect(gs.player):
					collected_coins += 1
				elif c.top > gs.HEIGHT:
					continue
				else:
					next_coin_list.append(c)
			if collected_coins:
				gs.coins += collected_coins
				queue_save()
			gs.coin_list = next_coin_list

			next_dash_trail = []
			for p in gs.dash_trail:
				p["life"] = update_timer(p["life"], dt)
				if p["life"] > 0:
					next_dash_trail.append(p)
			gs.dash_trail = next_dash_trail

			for p in gs.dash_trail:
				rect = p["rect"]
				alpha = int(20 + p["life"] * 8)
				glow = get_trail_surface((rect.width, rect.height), alpha)
				gs.screen.blit(glow, (rect.x - 15, rect.y - 15))

			for m in gs.magma_list:
				draw_magma(m)

			for c in gs.coin_list:
				draw_coin(c, tick)

			draw_player()

			if gs.shield:
				pulse = 28 + int((math.sin(tick * 0.03) + 1) * 2)
				draw_glow_circle(gs.player.center, pulse, GREEN, 75)
				pygame.draw.circle(gs.screen, GREEN, gs.player.center, pulse, 3)
			elif gs.shield_flash > 0:
				draw_glow_circle(gs.player.center, 28 + gs.shield_flash, BLUE, 60)

			draw_hud()
			draw_ability_bar()

		elif gs.game_state == "menu":
			draw_menu()
			draw_info_hub()

		elif gs.game_state == "settings":
			draw_settings()
			draw_info_hub()

		elif gs.game_state == "shop":
			draw_shop()
			draw_info_hub()

		elif gs.game_state == "pause":
			draw_pause()
			draw_info_hub()

		elif gs.game_state == "gameover":
			draw_gameover()
			draw_info_hub()

		if gs.console_open:
			draw_console()

		if gs.WIDTH == gs.window_w and gs.HEIGHT == gs.window_h:
			gs.display_screen.blit(gs.screen, (0, 0))
		else:
			scaled_screen = pygame.transform.scale(gs.screen, gs.display_screen.get_size())
			gs.display_screen.blit(scaled_screen, (0, 0))

		pygame.display.flip()


if __name__ == "__main__":
	main()
