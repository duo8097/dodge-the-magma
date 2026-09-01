import pygame
import sys

import py_version.many_file_ver.game_state as gs
from py_version.many_file_ver.constants import (
	DEFAULT_WIDTH, DEFAULT_HEIGHT, MIN_WIDTH, MIN_HEIGHT,
	WHITE, BLUE, GREEN, BG, GRID,
)


def apply_display_settings(new_full, new_w, new_h, scale_str):
	gs.ui_scale_str = scale_str
	gs.fullscreen = new_full
	gs.window_w = new_w
	gs.window_h = new_h

	if gs.fullscreen:
		gs.display_screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
		gs.window_w, gs.window_h = gs.display_screen.get_size()
	else:
		gs.display_screen = pygame.display.set_mode((gs.window_w, gs.window_h))

	scale_factor = 1.0
	if scale_str == "Auto":
		if gs.window_w >= 3840:
			scale_factor = 2.0
		elif gs.window_w >= 2560:
			scale_factor = 1.5
		elif gs.window_w >= 1920:
			scale_factor = 1.25
		else:
			scale_factor = 1.0
	else:
		try:
			scale_factor = float(scale_str.replace('%', '')) / 100.0
		except ValueError:
			scale_factor = 1.0

	gs.WIDTH = int(gs.window_w / scale_factor)
	gs.HEIGHT = int(gs.window_h / scale_factor)
	gs.screen = pygame.Surface((gs.WIDTH, gs.HEIGHT))


def run_startup_screen(startup):
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
