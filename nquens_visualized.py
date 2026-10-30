"""N-Queens exhaustive search, visualized live with pygame.

Every permutation of the columns (one queen per row and column) is generated
and tested for diagonal conflicts. Queens are placed on the board one at a
time, row by row; each step places one queen. When a new candidate shares its
first rows with the previous one (lexicographic order), those queens stay and
only the changed rows are re-placed. The search stops at the first valid
solution and reports how long it took.

Two algorithms (switch on the start screen with TAB):
    Backtracking  Place a queen, check the board right away. If the new queen
                  is attacked, try the next column; if a row runs out of
                  columns, remove the previous queen and try again (as in
                  the Wikipedia N-queens animation).
    Exhaustive    Generate every column permutation and test it once all
                  queens are down.

Start screen:
    UP/RIGHT, DOWN/LEFT, or type a number   choose n (2-12)
    TAB                                     switch algorithm
    ENTER                                   start the search

During the search:
    SPACE      pause / resume
    UP / DOWN  faster / slower (the top speed is MAX)
    RIGHT      single step (while paused)
    R          restart with the same n
    M          back to the start screen (change n)
    ESC        quit

Two times are reported:
    Elapsed       wall-clock time the search has been running (excludes pauses).
                  This depends on the visualization speed you chose.
    Search time   time spent purely inside the search code. This barely
                  depends on speed; use MAX speed for the most honest number.
"""

import math
import sys
import time
from itertools import permutations

import pygame

# ----------------------------------------------------------------- search ---

MIN_N, MAX_N = 2, 16


def find_conflict(placement):
    """Return (row1, row2) of the first diagonal-sharing pair, or None.
    placement[row] = column of the queen in that row."""
    n = len(placement)
    for r1 in range(n):
        for r2 in range(r1 + 1, n):
            if abs(placement[r1] - placement[r2]) == r2 - r1:
                return (r1, r2)
    return None


class Search:
    kind = "exhaustive"
    backtracks = 0

    def __init__(self, n):
        self.n = n
        self.total = math.factorial(n)
        self.gen = permutations(range(n))
        self.target = None  # the full permutation currently being built
        self.placed = []  # queens on the board so far (column per row)
        self.conflict = None
        self.checked = 0
        self.solution = None
        self.done = False
        self.elapsed = 0.0  # wall-clock running time (no pauses)
        self.search_time = 0.0  # time spent inside step()

    def step(self):
        """Place one queen. Once all n are down, test the candidate.
        Stops for good at the first solution."""
        if self.done:
            return
        if self.target is None or len(self.placed) == self.n:
            # Start the next candidate. Queens in the shared prefix stay put.
            try:
                nxt = next(self.gen)
            except StopIteration:
                self.done = True
                return
            keep = 0
            if self.target is not None:
                while keep < self.n and self.target[keep] == nxt[keep]:
                    keep += 1
            self.target = nxt
            self.placed = list(nxt[:keep])
        self.conflict = None
        self.placed.append(self.target[len(self.placed)])
        if len(self.placed) == self.n:
            self.checked += 1
            self.conflict = find_conflict(self.target)
            if self.conflict is None:
                self.solution = self.target
                self.done = True
            elif self.checked == self.total:
                self.done = True  # exhausted, no solution exists

    def run_steps(self, count=None, budget=None):
        """Run `count` steps, or steps for `budget` seconds. Times the work."""
        t0 = time.perf_counter()
        if count is not None:
            for _ in range(count):
                self.step()
                if self.done:
                    break
        else:
            while not self.done and time.perf_counter() - t0 < budget:
                for _ in range(500):
                    self.step()
                    if self.done:
                        break
        self.search_time += time.perf_counter() - t0


class BacktrackSearch(Search):
    """Depth-first search that validates the board after every queen.
    One step = one placement attempt (place a queen, then check it)."""

    kind = "backtracking"

    def __init__(self, n):
        super().__init__(n)
        self.total = None
        self.next_col = 0  # column to try in the current row
        self.bad = False  # last placed queen is in conflict and must go
        self.backtracks = 0

    def check_last(self):
        """Conflict between the newest queen and an earlier one, or None."""
        r = len(self.placed) - 1
        c = self.placed[r]
        for i in range(r):
            if self.placed[i] == c or abs(self.placed[i] - c) == r - i:
                return (i, r)
        return None

    def step(self):
        if self.done:
            return
        # Clean up after the previous attempt.
        if self.bad:
            self.next_col = self.placed.pop() + 1
            self.bad = False
        # Row exhausted: backtrack to the previous row.
        while self.next_col >= self.n:
            if not self.placed:
                self.done = True  # whole tree explored, no solution
                self.conflict = None
                return
            self.next_col = self.placed.pop() + 1
            self.backtracks += 1
        # Place a queen and validate the board right away.
        self.placed.append(self.next_col)
        self.checked += 1
        self.conflict = self.check_last()
        if self.conflict:
            self.bad = True
        else:
            self.next_col = 0
            if len(self.placed) == self.n:
                self.solution = tuple(self.placed)
                self.done = True


# --------------------------------------------------------------- drawing ----

W, H = 1100, 760
BOARD_PX = 640
BOARD_X, BOARD_Y = 30, 90
PANEL_X = BOARD_X + BOARD_PX + 30

BG = (24, 26, 33)
LIGHT = (236, 217, 181)
DARK = (176, 128, 92)
TEXT = (230, 230, 235)
MUTED = (140, 145, 160)
GREEN = (80, 200, 120)
RED = (230, 70, 70)
GOLD = (250, 205, 70)

# Candidates per second; None = MAX (as many as fit in each frame).
SPEEDS = [1, 2, 5, 10, 30, 60, 120, 600, 3000, 12000, 60000, None]
MAX_FRAME_BUDGET = 0.012  # seconds of searching per frame at MAX speed

_fonts = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("arial", size, bold=bold)
    return _fonts[key]


def draw_text(surf, text, pos, size=18, color=TEXT, bold=False, center=False):
    img = font(size, bold).render(text, True, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surf.blit(img, rect)


def fmt_time(seconds):
    if seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    return f"{seconds:.3f} s"


def draw_board(surf, x, y, size, n, placement, conflict, solved):
    cell = size / n
    for r in range(n):
        for c in range(n):
            color = LIGHT if (r + c) % 2 == 0 else DARK
            pygame.draw.rect(
                surf, color, (x + c * cell, y + r * cell, math.ceil(cell), math.ceil(cell))
            )
    if placement:
        bad_rows = set(conflict) if conflict else set()
        centers = [
            (x + c * cell + cell / 2, y + r * cell + cell / 2)
            for r, c in enumerate(placement)
        ]
        if conflict:
            pygame.draw.line(surf, RED, centers[conflict[0]], centers[conflict[1]], 5)
        qfont = font(max(10, int(cell * 0.4)), bold=True)
        for r, (cx, cy) in enumerate(centers):
            if solved:
                color = GREEN
            elif r in bad_rows:
                color = RED
            else:
                color = (40, 40, 48)
            radius = cell * 0.36
            pygame.draw.circle(surf, color, (cx, cy), radius)
            pygame.draw.circle(surf, (250, 250, 250), (cx, cy), radius, 3)
            glyph = qfont.render("Q", True, (250, 250, 250))
            surf.blit(glyph, glyph.get_rect(center=(cx, cy)))

    if solved:
        border = GREEN
    elif conflict:
        border = RED
    else:
        border = MUTED
    pygame.draw.rect(surf, border, (x - 2, y - 2, size + 4, size + 4), 4)


def draw_menu(screen, n, typed, algo):
    screen.fill(BG)
    draw_text(screen, "N-Queens Search Visualizer", (W // 2, 130), 44, TEXT, True, True)
    if algo == "backtracking":
        desc = "Places a queen, checks the board, and backtracks when stuck."
    else:
        desc = "Tries every column permutation until it finds the first valid solution."
    draw_text(screen, desc, (W // 2, 185), 20, MUTED, False, True)
    draw_text(screen, "Algorithm (TAB to switch)", (W // 2, 235), 18, MUTED, False, True)
    for i, (key, label) in enumerate([("backtracking", "Backtracking"), ("exhaustive", "Exhaustive")]):
        r = pygame.Rect(0, 0, 200, 40)
        r.center = (W // 2 - 110 + i * 220, 275)
        active = algo == key
        pygame.draw.rect(screen, (40, 43, 55), r, border_radius=10)
        pygame.draw.rect(screen, GOLD if active else (70, 73, 85), r, 3 if active else 1, border_radius=10)
        draw_text(screen, label, r.center, 20, GOLD if active else MUTED, active, True)

    draw_text(screen, "Board size (n)", (W // 2, 330), 24, MUTED, False, True)
    box = pygame.Rect(0, 0, 160, 120)
    box.center = (W // 2, 410)
    pygame.draw.rect(screen, (40, 43, 55), box, border_radius=14)
    pygame.draw.rect(screen, GOLD, box, 3, border_radius=14)
    draw_text(screen, str(n), box.center, 72, GOLD, True, True)
    draw_text(screen, "<", (box.left - 40, box.centery), 48, MUTED, True, True)
    draw_text(screen, ">", (box.right + 40, box.centery), 48, MUTED, True, True)

    if algo == "exhaustive":
        info = f"{n}x{n} board  -  {math.factorial(n):,} candidates to search at most"
    else:
        info = f"{n}x{n} board"
    draw_text(screen, info, (W // 2, 490), 20, TEXT, False, True)
    draw_text(screen, "Arrow keys or type a number (2-12), then press ENTER to start",
              (W // 2, 560), 20, MUTED, False, True)
    if n >= 10 and algo == "exhaustive":
        draw_text(screen, "Large boards can take a while; use the MAX speed setting.",
                  (W // 2, 595), 18, RED, False, True)


def draw_search(screen, search, speed_idx, paused):
    screen.fill(BG)
    name = "Backtracking" if search.kind == "backtracking" else "Exhaustive"
    draw_text(screen, f"{name} N-Queens  (n = {search.n})", (30, 22), 30, TEXT, True)
    draw_text(screen, "Queens are placed one at a time; stops at the first solution", (30, 62), 18, MUTED)

    solved = search.solution is not None
    draw_board(screen, BOARD_X, BOARD_Y, BOARD_PX, search.n,
               search.placed, search.conflict, solved)

    # verdict under board
    if solved:
        verdict, vcolor = "SOLUTION FOUND - no shared diagonals", GREEN
    elif search.done:
        verdict, vcolor = f"No solution exists for n = {search.n}", RED
    elif search.conflict:
        r1, r2 = search.conflict
        verdict, vcolor = f"Invalid - rows {r1} & {r2} share a diagonal", RED
    elif search.placed:
        verdict = f"Placing queens... ({len(search.placed)} / {search.n})"
        vcolor = MUTED
    else:
        verdict, vcolor = "Ready", MUTED
    draw_text(screen, verdict, (BOARD_X, BOARD_Y + BOARD_PX + 18), 24, vcolor, True)

    # progress bar
    bar_y = BOARD_Y + BOARD_PX + 58
    pygame.draw.rect(screen, (50, 53, 64), (BOARD_X, bar_y, BOARD_PX, 14), border_radius=7)
    if search.total:
        frac = search.checked / search.total
    else:  # backtracking: progress = how far the first queen has moved across
        frac = 1.0 if search.done and search.solution else (
            search.placed[0] / search.n if search.placed else 0.0)
    pygame.draw.rect(screen, GOLD, (BOARD_X, bar_y, max(0, BOARD_PX * frac), 14), border_radius=7)

    # stats panel
    px = PANEL_X
    if search.total:
        draw_text(screen, "Candidates checked", (px, 90), 18, MUTED)
        draw_text(screen, f"{search.checked:,} / {search.total:,}", (px, 112), 24, TEXT, True)
    else:
        draw_text(screen, "Placements tried / backtracks", (px, 90), 18, MUTED)
        draw_text(screen, f"{search.checked:,} / {search.backtracks:,}", (px, 112), 24, TEXT, True)

    if paused:
        status = "PAUSED"
    elif search.done:
        status = "DONE"
    else:
        status = "RUNNING"
    speed = SPEEDS[speed_idx]
    speed_txt = "MAX" if speed is None else f"{speed:,} queens/sec"
    draw_text(screen, f"{status}    speed: {speed_txt}", (px, 160), 18, GOLD)

    draw_text(screen, "Elapsed", (px, 205), 18, MUTED)
    draw_text(screen, fmt_time(search.elapsed), (px, 227), 24, TEXT, True)
    draw_text(screen, "Search time (compute only)", (px, 270), 18, MUTED)
    draw_text(screen, fmt_time(search.search_time), (px, 292), 24, TEXT, True)

    # result card
    card = pygame.Rect(px, 350, W - px - 30, 210)
    pygame.draw.rect(screen, (34, 37, 47), card, border_radius=12)
    if solved:
        pygame.draw.rect(screen, GREEN, card, 2, border_radius=12)
        draw_text(screen, "First solution found!", (card.x + 16, card.y + 14), 22, GREEN, True)
        draw_text(screen, f"After {search.checked:,} " + ("candidates" if search.total else "placements"), (card.x + 16, card.y + 50), 18)
        draw_text(screen, f"Search time: {fmt_time(search.search_time)}", (card.x + 16, card.y + 76), 18)
        draw_text(screen, f"Elapsed:     {fmt_time(search.elapsed)}", (card.x + 16, card.y + 102), 18)
        cols = ", ".join(str(c) for c in search.solution)
        draw_text(screen, "Column per row:", (card.x + 16, card.y + 138), 16, MUTED)
        draw_text(screen, f"[{cols}]", (card.x + 16, card.y + 160), 18)
    elif search.done:
        pygame.draw.rect(screen, RED, card, 2, border_radius=12)
        draw_text(screen, "No solution", (card.x + 16, card.y + 14), 22, RED, True)
        msg = (f"All {search.total:,} candidates tested" if search.total
               else f"Whole tree explored ({search.checked:,} placements)")
        draw_text(screen, msg, (card.x + 16, card.y + 50), 18)
        draw_text(screen, f"Search time: {fmt_time(search.search_time)}", (card.x + 16, card.y + 76), 18)
    else:
        draw_text(screen, "Searching...", (card.x + 16, card.y + 14), 22, MUTED, True)
        draw_text(screen, "The result and timing will appear here", (card.x + 16, card.y + 50), 16, MUTED)

    draw_text(screen, "SPACE pause   UP/DOWN speed", (px, 590), 14, MUTED)
    draw_text(screen, "RIGHT step   R restart   M change n", (px, 610), 14, MUTED)


# ------------------------------------------------------------------ main ----


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("N-Queens Search Visualizer")
    clock = pygame.time.Clock()

    mode = "menu"
    n = 8
    algo = "backtracking"
    typed = ""
    search = None
    speed_idx = 5
    paused = False
    accumulator = 0.0

    def start(new_n):
        nonlocal search, accumulator, paused
        search = BacktrackSearch(new_n) if algo == "backtracking" else Search(new_n)
        accumulator = 0.0
        paused = False

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif mode == "menu":
                    if event.key == pygame.K_TAB:
                        algo = "exhaustive" if algo == "backtracking" else "backtracking"
                    elif event.key in (pygame.K_UP, pygame.K_RIGHT):
                        n = min(n + 1, MAX_N)
                        typed = ""
                    elif event.key in (pygame.K_DOWN, pygame.K_LEFT):
                        n = max(n - 1, MIN_N)
                        typed = ""
                    elif event.key == pygame.K_BACKSPACE:
                        typed = typed[:-1]
                        n = int(typed) if typed else n
                    elif event.unicode.isdigit():
                        candidate = typed + event.unicode
                        if int(candidate) > MAX_N:
                            candidate = event.unicode
                        typed = candidate
                        n = max(MIN_N, min(MAX_N, int(typed)))
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        typed = ""
                        start(n)
                        mode = "search"
                else:
                    if event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key == pygame.K_UP:
                        speed_idx = min(speed_idx + 1, len(SPEEDS) - 1)
                    elif event.key == pygame.K_DOWN:
                        speed_idx = max(speed_idx - 1, 0)
                    elif event.key == pygame.K_RIGHT:
                        paused = True
                        if not search.done:
                            search.run_steps(count=1)
                    elif event.key == pygame.K_r:
                        start(n)
                    elif event.key == pygame.K_m:
                        mode = "menu"

        if mode == "menu":
            draw_menu(screen, n, typed, algo)
        else:
            if not paused and not search.done:
                search.elapsed += dt
                speed = SPEEDS[speed_idx]
                if speed is None:
                    search.run_steps(budget=MAX_FRAME_BUDGET)
                else:
                    accumulator += speed * dt
                    steps = int(accumulator)
                    accumulator -= steps
                    if steps:
                        search.run_steps(count=steps)
            draw_search(screen, search, speed_idx, paused)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()