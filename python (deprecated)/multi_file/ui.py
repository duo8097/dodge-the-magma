import pygame

import py_version.many_file_ver.game_state as gs
from py_version.many_file_ver.constants import (
	WHITE, RED, BLUE, GREEN, YELLOW, PURPLE, SHOP_ITEMS,
)
from py_version.many_file_ver.helpers import draw_box, draw_text, clamp


def draw_hud():
	panel_x = 10
	panel_y = 10
	draw_box(panel_x, panel_y, 320, 108, (0, 0, 0), WHITE)

	score_surf = gs.font.render(f"SCORE: {gs.score}", True, WHITE)
	coin_surf = gs.font.render(f"COINS: {gs.coins}", True, YELLOW)
	speed_surf = gs.small_font.render(f"SPD: {gs.player_speed}", True, BLUE)
	jump_surf = gs.small_font.render(f"JUMPS: {gs.jumps_left}/{gs.max_jumps}", True, GREEN)
	gs.screen.blit(score_surf, (22, 20))
	gs.screen.blit(coin_surf, (22, 52))
	gs.screen.blit(speed_surf, (22, 90))
	gs.screen.blit(jump_surf, (150, 90))


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
			"ratio": 1.0 if gs.dash_cooldown <= 0 else 1 - gs.dash_cooldown / 60,
			"color": BLUE,
			"active": gs.dash_cooldown <= 0,
		},
		{
			"label": "SHIELD",
			"key": "[E]",
			"ratio": 1.0 if gs.shield_cooldown <= 0 else 1 - gs.shield_cooldown / gs.shield_cooldown_real,
			"color": GREEN,
			"active": gs.shield or gs.shield_cooldown <= 0,
		},
	]

	total_w = slot_w * 2 + slot_gap
	start_x = gs.WIDTH // 2 - total_w // 2
	center_y = gs.HEIGHT - 55

	for i, slot in enumerate(slots):
		x = start_x + i * (slot_w + slot_gap)

		icon_y = center_y - icon_size // 2
		icon_border = slot["color"] if slot["active"] else (58, 58, 90)
		icon_bg = (10, 22, 12) if slot["color"] == GREEN else (10, 16, 32)
		icon_bg = icon_bg if slot["active"] else (17, 17, 34)
		pygame.draw.rect(gs.screen, icon_bg, (x, icon_y, icon_size, icon_size), border_radius=6)
		pygame.draw.rect(gs.screen, icon_border, (x, icon_y, icon_size, icon_size), 1, border_radius=6)

		if slot["active"]:
			pygame.draw.circle(gs.screen, slot["color"], (x + icon_size - 6, icon_y + 6), 3)

		bar_x = x + icon_size + icon_bar_gap

		label_h = gs.small_font.get_height()
		key_h = gs.small_font.get_height()
		content_h = label_h + 4 + bar_h + 4 + key_h
		text_y = center_y - content_h // 2

		label_surface = gs.small_font.render(slot["label"], True, (180, 180, 210))
		gs.screen.blit(label_surface, (bar_x, text_y))

		bar_y = text_y + label_h + 4
		pygame.draw.rect(gs.screen, (26, 26, 46), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
		pygame.draw.rect(gs.screen, (58, 58, 90), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=6)

		fill_w = max(0, int(bar_w * clamp(slot["ratio"], 0, 1)))
		if fill_w > 0:
			pygame.draw.rect(gs.screen, slot["color"], (bar_x, bar_y, fill_w, bar_h), border_radius=6)

		key_surface = gs.small_font.render(slot["key"], True, (90, 90, 120))
		gs.screen.blit(key_surface, (bar_x, bar_y + bar_h + 4))


def draw_info_hub():
	hub_w = 220
	hub_h = 72
	hub_x = gs.WIDTH - hub_w - 12
	hub_y = 12
	draw_box(hub_x, hub_y, hub_w, hub_h, (0, 0, 0), WHITE)

	coins_surf = gs.small_font.render(f"COINS: {gs.coins}", True, YELLOW)
	score_surf = gs.small_font.render(f"SCORE: {gs.score}", True, WHITE)
	gs.screen.blit(coins_surf, (hub_x + 16, hub_y + 14))
	gs.screen.blit(score_surf, (hub_x + 16, hub_y + 40))


def draw_menu():
	draw_box(gs.WIDTH // 2 - 260, 170, 520, 400, (0, 0, 0), WHITE)

	y = 210
	gap = 42

	gs.screen.blit(
		gs.big_font.render("DODGE THE MAGMA", True, WHITE),
		(gs.WIDTH // 2 - 230, y),
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
	draw_text(f"COINS: {gs.coins}", y, YELLOW)


def get_settings_rects():
	px = gs.WIDTH // 2 - 300
	py = 150

	btn_window = pygame.Rect(px + 40, py + 60, 175, 32)
	btn_full = pygame.Rect(px + 225, py + 60, 175, 32)

	preset_rects = []
	for i in range(len(gs.settings_presets)):
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
	px = gs.WIDTH // 2 - 300
	py = 150
	draw_box(px, py, 600, 430, (0, 0, 0), WHITE)

	draw_text("=== SETTINGS ===", py + 15, PURPLE, gs.small_font)

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

	gs.screen.blit(f_small.render("DISPLAY MODE", True, (140, 140, 180)), (px + 40, py + 42))
	draw_btn(gs.screen, btn_window, "WINDOW", not gs.settings_fullscreen, BLUE)
	draw_btn(gs.screen, btn_full, "FULLSCREEN", gs.settings_fullscreen, BLUE)

	res_alpha = 80 if gs.settings_fullscreen else 255
	resolution_label = f_small.render("RESOLUTION", True, (140, 140, 180))
	resolution_label.set_alpha(res_alpha)
	gs.screen.blit(resolution_label, (px + 40, py + 106))

	for i, (preset_w, preset_h) in enumerate(gs.settings_presets):
		if not gs.settings_fullscreen:
			draw_btn(gs.screen, preset_rects[i], f"{preset_w}x{preset_h}", gs.settings_selected_preset == i, GREEN)
		else:
			pygame.draw.rect(gs.screen, (17, 17, 34), preset_rects[i], border_radius=6)
			pygame.draw.rect(gs.screen, (40, 40, 60), preset_rects[i], 1, border_radius=6)

	if not gs.settings_fullscreen:
		draw_btn(gs.screen, custom_rect, "custom", gs.settings_selected_preset == -1, GREEN)

	if gs.settings_selected_preset == -1 and not gs.settings_fullscreen:
		for rect, value, field in (
			(width_rect, gs.settings_custom_w, "w"),
			(height_rect, gs.settings_custom_h, "h"),
		):
			border = BLUE if gs.settings_active_field == field else (58, 58, 90)
			pygame.draw.rect(gs.screen, (11, 11, 22), rect, border_radius=6)
			pygame.draw.rect(gs.screen, border, rect, 1, border_radius=6)
			value_surface = f_med.render(value, True, WHITE)
			gs.screen.blit(value_surface, value_surface.get_rect(center=rect.center))
		gs.screen.blit(f_small.render("x", True, (80, 80, 110)), (px + 128, py + 204))

	gs.screen.blit(f_small.render("TARGET FPS", True, (140, 140, 180)), (px + 40, py + 232))
	fps_options = [30, 60, 120, 144]
	for i, fps in enumerate(fps_options):
		draw_btn(gs.screen, fps_rects[i], f"{fps} FPS", gs.settings_fps == fps, GREEN)

	gs.screen.blit(f_small.render("UI SCALE", True, (140, 140, 180)), (px + 40, py + 292))
	for i, scale_opt in enumerate(gs.settings_ui_scale_opts):
		draw_btn(gs.screen, scale_rects[i], scale_opt, gs.settings_scale_str == scale_opt, GREEN)

	draw_btn(gs.screen, apply_rect, "[ APPLY ]", True, WHITE)
	draw_btn(gs.screen, back_rect, "[ BACK ]", True, RED)


def draw_shop():
	draw_box(gs.WIDTH // 2 - 330, 110, 660, 480, (0, 0, 0), WHITE)

	real_mx, real_my = pygame.mouse.get_pos()
	scale_x = gs.WIDTH / gs.window_w
	scale_y = gs.HEIGHT / gs.window_h
	mouse = (int(real_mx * scale_x), int(real_my * scale_y))
	item_rects = []
	for i in range(len(SHOP_ITEMS)):
		item_rects.append(pygame.Rect(gs.WIDTH // 2 - 250, 170 + i * 85, 500, 70))

	draw_text("=== SHOP ===", 130, YELLOW)

	for item, item_rect in zip(SHOP_ITEMS, item_rects):
		hovered = item_rect.collidepoint(mouse)
		fill = (28, 28, 40) if not hovered else (50, 50, 72)
		border = item["color"] if hovered else WHITE
		pygame.draw.rect(gs.screen, fill, item_rect, border_radius=12)
		pygame.draw.rect(gs.screen, border, item_rect, 2, border_radius=12)

		icon = gs.small_font.render(f"[{item['label']}]", True, item["color"])
		title = gs.font.render(item["title"], True, WHITE)
		cost = gs.small_font.render(f"{item['cost']} coins", True, YELLOW)
		desc = gs.small_font.render(item["desc"], True, (180, 180, 190))

		gs.screen.blit(icon, (item_rect.x + 18, item_rect.y + 16))
		gs.screen.blit(title, (item_rect.x + 78, item_rect.y + 12))
		gs.screen.blit(desc, (item_rect.x + 78, item_rect.y + 38))
		gs.screen.blit(cost, (item_rect.right - cost.get_width() - 18, item_rect.y + 23))

	draw_text("[ ESC ] BACK", 520, WHITE)
	draw_text(f"COINS: {gs.coins}", 550, YELLOW)


def draw_pause():
	draw_box(gs.WIDTH // 2 - 250, 180, 500, 260, (0, 0, 0), BLUE)
	draw_text("PAUSED", 225, BLUE, gs.big_font)
	draw_text("[ ESC ] RESUME", 310, WHITE)
	draw_text("[ M ] MENU", 352, GREEN)
	draw_text("[ Q ] SAVE & QUIT", 394, RED)


def draw_gameover():
	draw_box(gs.WIDTH // 2 - 260, 160, 520, 380, (0, 0, 0), RED)

	y = 200
	gap = 38

	gs.screen.blit(
		gs.big_font.render("GAME OVER", True, RED),
		(gs.WIDTH // 2 - 150, y),
	)
	y += 72

	draw_text(f"SCORE: {gs.score}", y, WHITE)
	y += gap
	draw_text(f"COINS: {gs.coins}", y, YELLOW)
	y += gap
	draw_text("[ SPACE ] RETRY", y, BLUE)
	y += gap
	draw_text("[ M ] MENU", y, GREEN)
	y += gap
	draw_text("[ S ] SHOP", y, YELLOW)
	y += gap
	draw_text("[ Q ] EXIT", y, WHITE)
	if pygame.time.get_ticks() < gs.gameover_input_unlock_at:
		draw_text("Please wait...", y + 36, (180, 180, 180), gs.small_font)
