
import pygame
import sys
import random
from collections import deque



# ------------ Configuration ------------
GRID_W, GRID_H = 10, 20          # standard Tetris field
BLOCK = 30                        # pixel size of one cell

PADDING = 12                      # UI padding
PANEL_W = 8 * BLOCK               # right side panel width
TOP_BAR_H = 56                    # top title/status bar height

WIDTH = GRID_W * BLOCK + PANEL_W + PADDING * 3
HEIGHT = TOP_BAR_H + GRID_H * BLOCK + PADDING * 2
FPS = 60

# Layout anchors
PLAY_X = PADDING                  # left of playfield
PLAY_Y = TOP_BAR_H                # below title bar
PANEL_X = PLAY_X + GRID_W * BLOCK + PADDING  # right panel start
PANEL_Y = TOP_BAR_H + PADDING

# Colors
BG = (18, 18, 22)
BOARD_BG = (28, 28, 34)
GRID_LINE = (45, 45, 55)
BORDER = (90, 90, 105)
TEXT = (235, 235, 245)
SUBTEXT = (190, 190, 205)
GHOST = (170, 170, 190)

COLORS = {
    'I': (0, 240, 240),
    'O': (240, 240, 0),
    'T': (160, 0, 240),
    'S': (0, 240, 0),
    'Z': (240, 0, 0),
    'J': (0, 0, 240),
    'L': (240, 160, 0),
}

# Tetromino definitions as rotation states (list of matrices)
SHAPES = {
    'I': [
        [[0,0,0,0],
         [1,1,1,1],
         [0,0,0,0],
         [0,0,0,0]],
        [[0,0,1,0],
         [0,0,1,0],
         [0,0,1,0],
         [0,0,1,0]],
    ],
    'O': [
        [[1,1],
         [1,1]],
    ],
    'T': [
        [[0,1,0],
         [1,1,1],
         [0,0,0]],
        [[0,1,0],
         [0,1,1],
         [0,1,0]],
        [[0,0,0],
         [1,1,1],
         [0,1,0]],
        [[0,1,0],
         [1,1,0],
         [0,1,0]],
    ],
    'S': [
        [[0,1,1],
         [1,1,0],
         [0,0,0]],
        [[0,1,0],
         [0,1,1],
         [0,0,1]],
    ],
    'Z': [
        [[1,1,0],
         [0,1,1],
         [0,0,0]],
        [[0,0,1],
         [0,1,1],
         [0,1,0]],
    ],
    'J': [
        [[1,0,0],
         [1,1,1],
         [0,0,0]],
        [[0,1,1],
         [0,1,0],
         [0,1,0]],
        [[0,0,0],
         [1,1,1],
         [0,0,1]],
        [[0,1,0],
         [0,1,0],
         [1,1,0]],
    ],
    'L': [
        [[0,0,1],
         [1,1,1],
         [0,0,0]],
        [[0,1,0],
         [0,1,0],
         [0,1,1]],
        [[0,0,0],
         [1,1,1],
         [1,0,0]],
        [[1,1,0],
         [0,1,0],
         [0,1,0]],
    ],
}

def matrix_to_coords(matrix):
    coords = []
    for y, row in enumerate(matrix):
        for x, v in enumerate(row):
            if v:
                coords.append((x, y))
    minx = min(c[0] for c in coords)
    miny = min(c[1] for c in coords)
    return [(x - minx, y - miny) for (x, y) in coords]

ROTATIONS = {name: [matrix_to_coords(m) for m in mats] for name, mats in SHAPES.items()}

KICKS = {'default': [(0,0), (1,0), (-1,0), (0,-1), (2,0), (-2,0)],
         'I': [(0,0), (1,0), (-1,0), (2,0), (-2,0), (0,-1)]}

def bag_generator():
    while True:
        bag = list(ROTATIONS.keys())
        random.shuffle(bag)
        for p in bag:
            yield p

class Piece:
    def __init__(self, name):
        self.name = name
        self.rots = ROTATIONS[name]
        self.r = 0
        self.x = GRID_W // 2 - 2
        self.y = -2
        self.used_hold = False

    @property
    def cells(self):
        return self.rots[self.r]

    def move(self, dx, dy, board):
        if not collision(self, board, self.x + dx, self.y + dy, self.r):
            self.x += dx
            self.y += dy
            return True
        return False

    def rotate(self, dr, board):
        if self.name == 'O':
            return False
        nr = (self.r + dr) % len(self.rots)
        kicks = KICKS['I'] if self.name == 'I' else KICKS['default']
        for (kx, ky) in kicks:
            if not collision(self, board, self.x + kx, self.y + ky, nr):
                self.x += kx
                self.y += ky
                self.r = nr
                return True
        return False

    def hard_drop_distance(self, board):
        dy = 0
        while not collision(self, board, self.x, self.y + dy + 1, self.r):
            dy += 1
        return dy

def make_board():
    return [[None for _ in range(GRID_W)] for _ in range(GRID_H)]

def collision(piece, board, x, y, r):
    for (cx, cy) in piece.rots[r]:
        gx, gy = x + cx, y + cy
        if gx < 0 or gx >= GRID_W or gy >= GRID_H:
            return True
        if gy >= 0 and board[gy][gx] is not None:
            return True
    return False

def lock_piece(piece, board):
    for (cx, cy) in piece.cells:
        gx, gy = piece.x + cx, piece.y + cy
        if 0 <= gy < GRID_H:
            board[gy][gx] = COLORS[piece.name]

def clear_lines(board):
    full_rows = [i for i, row in enumerate(board) if all(cell is not None for cell in row)]
    for i in full_rows:
        del board[i]
        board.insert(0, [None for _ in range(GRID_W)])
    return len(full_rows)

def draw_block(surf, x, y, color, alpha=None):
    rect = pygame.Rect(x, y, BLOCK, BLOCK)
    if alpha is not None:
        s = pygame.Surface((BLOCK, BLOCK), pygame.SRCALPHA)
        s.fill((*color, alpha))
        surf.blit(s, rect.topleft)
        pygame.draw.rect(surf, BORDER, rect, 1)
    else:
        pygame.draw.rect(surf, color, rect)
        pygame.draw.rect(surf, BORDER, rect, 1)

def draw_board_bg(surf):
    # solid board background + grid
    board_rect = pygame.Rect(PLAY_X, PLAY_Y, GRID_W*BLOCK, GRID_H*BLOCK)
    pygame.draw.rect(surf, BOARD_BG, board_rect)
    # grid
    for y in range(GRID_H):
        for x in range(GRID_W):
            rx = PLAY_X + x * BLOCK
            ry = PLAY_Y + y * BLOCK
            pygame.draw.rect(surf, GRID_LINE, (rx, ry, BLOCK, BLOCK), 1)

def draw_board(surf, board):
    for y in range(GRID_H):
        for x in range(GRID_W):
            if board[y][x]:
                rx = PLAY_X + x * BLOCK
                ry = PLAY_Y + y * BLOCK
                draw_block(surf, rx, ry, board[y][x])

def draw_piece(surf, piece, color, y_offset=0, ghost=False):
    for (cx, cy) in piece.cells:
        rx = PLAY_X + (piece.x + cx) * BLOCK
        ry = PLAY_Y + (piece.y + cy + y_offset) * BLOCK
        if ghost:
            draw_block(surf, rx, ry, color, alpha=60)
        else:
            draw_block(surf, rx, ry, color)

def draw_preview_box(surf, title, piece_name, x, y, box_w=4, box_h=3):
    # frame
    outer = pygame.Rect(x, y, box_w*BLOCK, box_h*BLOCK)
    pygame.draw.rect(surf, BOARD_BG, outer)
    pygame.draw.rect(surf, BORDER, outer, 2)
    # label
    if title:
        label_rect = pygame.Rect(x, y - 20, 100, 18)
        # (draw text next to it in caller)
    # piece
    if piece_name:
        cells = ROTATIONS[piece_name][0]
        # center the piece
        minx = min(c[0] for c in cells); maxx = max(c[0] for c in cells)
        miny = min(c[1] for c in cells); maxy = max(c[1] for c in cells)
        w = maxx - minx + 1; h = maxy - miny + 1
        offset_x = x + (box_w*BLOCK - w*BLOCK)//2
        offset_y = y + (box_h*BLOCK - h*BLOCK)//2
        for (cx, cy) in cells:
            rx = offset_x + (cx - minx) * BLOCK
            ry = offset_y + (cy - miny) * BLOCK
            draw_block(surf, rx, ry, COLORS[piece_name])

def render_text(surf, text, font, color, x, y, align='left'):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if align == 'left':
        rect.topleft = (x, y)
    elif align == 'center':
        rect.midtop = (x, y)
    elif align == 'right':
        rect.topright = (x, y)
    surf.blit(img, rect)

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Tetris")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("consolas,arial", 32, bold=True)
        self.num_font = pygame.font.SysFont("consolas,arial", 22, bold=True)
        self.small = pygame.font.SysFont("consolas,arial", 18)
        self.reset()

    def reset(self):
        self.board = make_board()
        self.lines = 0
        self.level = 1
        self.score = 0
        self.drop_timer = 0.0
        self.soft_drop = False
        self.paused = False
        self.game_over = False
        self.can_hold = True

        self.generator = bag_generator()
        self.queue = deque([next(self.generator) for _ in range(5)])
        self.current = Piece(self.queue.popleft())
        self.hold = None

        self.gravity_base = 0.9
        self.gravity_min = 0.05

        self.move_dir = 0
        self.move_delay = 0.0
        self.move_interval = 0.05
        self.move_initial_delay = 0.15

    def next_piece(self):
        if len(self.queue) < 5:
            for _ in range(5 - len(self.queue)):
                self.queue.append(next(self.generator))
        self.current = Piece(self.queue.popleft())
        self.can_hold = True
        if collision(self.current, self.board, self.current.x, self.current.y, self.current.r):
            self.game_over = True

    def hold_piece(self):
        if not self.can_hold or self.game_over:
            return
        self.can_hold = False
        if self.hold is None:
            self.hold = self.current.name
            self.next_piece()
        else:
            self.current, self.hold = Piece(self.hold), self.current.name
            self.current.x = GRID_W // 2 - 2
            self.current.y = -2
            self.current.r = 0
            if collision(self.current, self.board, self.current.x, self.current.y, self.current.r):
                self.game_over = True

    def score_lines(self, ncleared):
        if ncleared == 0:
            return
        base = {1:100, 2:300, 3:500, 4:800}.get(ncleared, 0)
        gained = base * self.level
        self.score += gained
        self.lines += ncleared
        self.level = 1 + self.lines // 10

    def gravity_interval(self):
        t = self.gravity_base * (0.85 ** (self.level - 1))
        return max(self.gravity_min, t)

    def hard_drop(self):
        dy = self.current.hard_drop_distance(self.board)
        self.current.y += dy
        lock_piece(self.current, self.board)
        cleared = clear_lines(self.board)
        self.score += 2 * dy
        self.score_lines(cleared)
        self.next_piece()

    def update(self, dt):
        if self.paused or self.game_over:
            return

        if self.move_dir != 0:
            self.move_delay += dt
            if self.move_delay >= (self.move_initial_delay if self.move_delay < self.move_initial_delay else self.move_interval):
                moved = self.current.move(self.move_dir, 0, self.board)
                if self.move_delay < self.move_initial_delay:
                    self.move_delay = self.move_initial_delay
                else:
                    self.move_delay = 0 if moved else self.move_interval

        interval = self.gravity_interval()
        if self.soft_drop:
            interval *= 0.08
        self.drop_timer += dt
        if self.drop_timer >= interval:
            self.drop_timer = 0.0
            if not self.current.move(0, 1, self.board):
                lock_piece(self.current, self.board)
                cleared = clear_lines(self.board)
                if self.soft_drop:
                    self.score += 1
                self.score_lines(cleared)
                self.next_piece()

    def handle_keydown(self, key):
        if key in (pygame.K_LEFT, pygame.K_a):
            self.move_dir = -1
            self.move_delay = 0
            self.current.move(-1, 0, self.board)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.move_dir = 1
            self.move_delay = 0
            self.current.move(1, 0, self.board)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.soft_drop = True
        elif key in (pygame.K_UP, pygame.K_x):
            self.current.rotate(+1, self.board)
        elif key == pygame.K_z:
            self.current.rotate(-1, self.board)
        elif key == pygame.K_c or key == pygame.K_LSHIFT or key == pygame.K_RSHIFT:
            self.hold_piece()
        elif key == pygame.K_SPACE:
            self.hard_drop()
        elif key == pygame.K_p:
            self.paused = not self.paused
        elif key == pygame.K_r:
            self.reset()
        elif key in (pygame.K_q, pygame.K_ESCAPE):
            pygame.quit()
            sys.exit()

    def handle_keyup(self, key):
        if key in (pygame.K_LEFT, pygame.K_a) and self.move_dir == -1:
            self.move_dir = 0
            self.move_delay = 0
        elif key in (pygame.K_RIGHT, pygame.K_d) and self.move_dir == 1:
            self.move_dir = 0
            self.move_delay = 0
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.soft_drop = False

    def draw_top_bar(self):
        pygame.draw.rect(self.screen, BG, (0, 0, WIDTH, TOP_BAR_H))
        # Title
        render_text(self.screen, "TETRIS", self.title_font, TEXT, PADDING, 12, align='left')
        # Stats in top bar for compactness
        stats = f"Score {self.score}   Level {self.level}   Lines {self.lines}"
        render_text(self.screen, stats, self.small, SUBTEXT, WIDTH - PADDING, 18, align='right')

    def draw_right_panel(self):
        # Panel header text
        y = PANEL_Y
        render_text(self.screen, "Next", self.num_font, TEXT, PANEL_X, y-4)
        y += 4
        # Show up to 4 next pieces in framed boxes
        box_h_px = 3*BLOCK
        spacing = 10
        y_box = y + 16
        for name in list(self.queue)[:4]:
            draw_preview_box(self.screen, None, name, PANEL_X, y_box, box_w=4, box_h=3)
            y_box += box_h_px + spacing

        # Hold section
        y_hold_title = y_box + 8
        render_text(self.screen, "Hold", self.num_font, TEXT, PANEL_X, y_hold_title)
        y_hold_box = y_hold_title + 12
        draw_preview_box(self.screen, None, self.hold, PANEL_X, y_hold_box, box_w=4, box_h=3)

    def draw(self):
        # Background
        self.screen.fill(BG)
        # Top bar
        self.draw_top_bar()
        # Board background & grid
        draw_board_bg(self.screen)
        # Ghost piece
        ghost_dy = self.current.hard_drop_distance(self.board)
        draw_piece(self.screen, self.current, GHOST, y_offset=ghost_dy, ghost=True)
        # Current piece
        draw_piece(self.screen, self.current, COLORS[self.current.name])
        # Locked blocks
        draw_board(self.screen, self.board)
        # Border around board
        pygame.draw.rect(self.screen, BORDER, (PLAY_X-2, PLAY_Y-2, GRID_W*BLOCK+4, GRID_H*BLOCK+4), 2)
        # Right panel
        self.draw_right_panel()

        # Pause & Game Over overlays
        if self.paused:
            render_text(self.screen, "PAUSED (P)", self.title_font, TEXT, PLAY_X + GRID_W*BLOCK//2, PLAY_Y + GRID_H*BLOCK//2 - 16, align='center')
        if self.game_over:
            render_text(self.screen, "GAME OVER", self.title_font, TEXT, PLAY_X + GRID_W*BLOCK//2, PLAY_Y + GRID_H*BLOCK//2 - 28, align='center')
            render_text(self.screen, "R = Restart, Q = Quit", self.small, TEXT, PLAY_X + GRID_W*BLOCK//2, PLAY_Y + GRID_H*BLOCK//2 + 4, align='center')

        # Controls hint at bottom
        hint = "←→ Move  ↓ Soft  ↑/X Rotate  Z CCW  Space Hard  C Hold  P Pause"
        render_text(self.screen, hint, self.small, SUBTEXT, WIDTH//2, HEIGHT - PADDING - 16, align='center')

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    self.handle_keydown(event.key)
                elif event.type == pygame.KEYUP:
                    self.handle_keyup(event.key)

            self.update(dt)
            self.draw()
            pygame.display.flip()

if __name__ == "__main__":
    Game().run()
