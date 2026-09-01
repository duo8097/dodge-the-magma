import platform
import pygame

IS_WINDOWS = platform.system() == "Windows"

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
AUTO_SAVE_INTERVAL = 5000

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
