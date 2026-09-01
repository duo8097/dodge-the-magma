import pygame
from functools import lru_cache

import py_version.many_file_ver.game_state as gs
from py_version.many_file_ver.constants import WHITE, PANEL


def clamp(value, minimum, maximum):
	return max(minimum, min(maximum, value))


def draw_box(x, y, w, h, color=PANEL, border=WHITE, border_radius=10):
	pygame.draw.rect(gs.screen, color, (x, y, w, h), border_radius=border_radius)
	pygame.draw.rect(
		gs.screen, border, (x, y, w, h), 2, border_radius=border_radius
	)


def draw_text(text, y, color=WHITE, font_ref=None):
	if font_ref is None:
		font_ref = gs.font
	rendered = font_ref.render(text, True, color)
	gs.screen.blit(rendered, (gs.WIDTH // 2 - rendered.get_width() // 2, y))


def draw_bar(x, y, w, h, ratio, fill_color, label, border_color=WHITE):
	ratio = clamp(ratio, 0, 1)
	pygame.draw.rect(gs.screen, (25, 25, 35), (x, y, w, h), border_radius=8)
	pygame.draw.rect(gs.screen, border_color, (x, y, w, h), 2, border_radius=8)
	if ratio > 0:
		inner_w = max(0, int((w - 4) * ratio))
		pygame.draw.rect(
			gs.screen,
			fill_color,
			(x + 2, y + 2, inner_w, h - 4),
			border_radius=7,
		)
	label_surf = gs.small_font.render(label, True, WHITE)
	gs.screen.blit(label_surf, (x + 8, y + h // 2 - label_surf.get_height() // 2))


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
	if gs.magma_glow_surface is None:
		gs.magma_glow_surface = pygame.Surface((72, 72), pygame.SRCALPHA)
		pygame.draw.circle(gs.magma_glow_surface, (255, 110, 50, 80), (36, 36), 18)
		pygame.draw.circle(gs.magma_glow_surface, (255, 70, 40, 50), (36, 36), 26)
	return gs.magma_glow_surface


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
	gs.screen.blit(glow, (center[0] - radius * 2, center[1] - radius * 2))
