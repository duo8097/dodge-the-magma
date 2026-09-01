import math
import pygame

import py_version.many_file_ver.game_state as gs
from py_version.many_file_ver.constants import BLUE, WHITE, RED, ORANGE, YELLOW
from py_version.many_file_ver.helpers import get_magma_glow_surface, clamp


def draw_player():
	body_color = BLUE if not gs.shield else (135, 240, 255)
	lean = int(clamp(gs.velocity_y / 4, -4, 4))
	body = pygame.Rect(gs.player.x, gs.player.y, gs.player.width, gs.player.height)
	body.inflate_ip(-4, -4)

	pygame.draw.rect(
		gs.screen,
		(20, 40, 65),
		body.move(0, 4),
		border_radius=14,
	)
	pygame.draw.rect(
		gs.screen,
		body_color,
		body.move(lean, 0),
		border_radius=14,
	)

	eye_x = body.centerx + (7 if gs.facing > 0 else -14)
	pygame.draw.rect(
		gs.screen,
		WHITE,
		(eye_x, body.y + 12, 5, 5),
		border_radius=2,
	)
	pygame.draw.rect(
		gs.screen,
		(20, 20, 30),
		(eye_x + 1, body.y + 13, 2, 2),
		border_radius=1,
	)


def draw_magma(m):
	glow = get_magma_glow_surface()
	gs.screen.blit(glow, (m.centerx - 36, m.centery - 36))

	pygame.draw.rect(gs.screen, (130, 35, 20), m.inflate(-4, -4), border_radius=6)
	pygame.draw.rect(gs.screen, RED, m, border_radius=6)
	pygame.draw.rect(gs.screen, ORANGE, m.inflate(-14, -14), border_radius=4)


def draw_coin(c, tick):
	pulse = 1 + int((math.sin(tick * 0.02) + 1) * 1.5)
	pygame.draw.circle(gs.screen, (200, 160, 20), c.center, 11 + pulse // 3)
	pygame.draw.circle(gs.screen, YELLOW, c.center, 8 + pulse // 4)
	pygame.draw.circle(gs.screen, WHITE, (c.centerx - 3, c.centery - 3), 2)
	pygame.draw.line(
		gs.screen, WHITE, (c.centerx - 6, c.centery), (c.centerx + 6, c.centery), 1
	)
	pygame.draw.line(
		gs.screen, WHITE, (c.centerx, c.centery - 6), (c.centerx, c.centery + 6), 1
	)
