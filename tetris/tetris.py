#!/usr/bin/env python3
"""
ASCII Tetris for the terminal, with a looping chiptune background track.
Works on Windows (cmd, PowerShell, Windows Terminal), Linux, macOS and Termux.

Controls
  Left / Right    move
  Up              rotate
  Down            soft drop
  Page Down       hard drop
  Enter           hard drop
  Insert          hard drop
  Home            pause / resume
  End             restart
  Esc or Ctrl+C   quit

Run:    python tetris.py
Flags:  --mono       no colors
        --no-sound   no background music
"""

import array
import os
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave

WIDTH = 10
HEIGHT = 20
LINE_POINTS = {1: 100, 2: 300, 3: 500, 4: 800}

SHAPES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[0, 1, 0], [1, 1, 1]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "Z": [[1, 1, 0], [0, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
}
COLORS = {"I": 96, "O": 93, "T": 95, "S": 92, "Z": 91, "J": 94, "L": 33, "GHOST": 90, "MSG": 97}
MONO = "--mono" in sys.argv
NO_SOUND = "--no-sound" in sys.argv

# Single bytes that map to actions (Esc is handled separately).
CHAR_KEYS = {"\x03": "QUIT", "\r": "DROP", "\n": "DROP"}          # Ctrl+C quits, Enter drops

# Escape sequences after ESC (Unix terminals).
ESC_SEQUENCES = {
    b"[A": "UP", b"[B": "DOWN", b"[C": "RIGHT", b"[D": "LEFT",
    b"OA": "UP", b"OB": "DOWN", b"OC": "RIGHT", b"OD": "LEFT",
    b"[6~": "DROP", b"[2~": "DROP",                                              # Page Down
    b"[1~": "PAUSE", b"[7~": "PAUSE", b"[H": "PAUSE", b"OH": "PAUSE",  # Home
    b"[4~": "RESTART", b"[8~": "RESTART", b"[F": "RESTART", b"OF": "RESTART",  # End
}


# ---------------------------------------------------------------- input ----

def parse_keys(data):
    """Turn raw bytes from a Unix terminal into action names."""
    keys = []
    i = 0
    while i < len(data):
        b = data[i]
        if b == 0x1B:
            if i + 1 == len(data):          # lone Esc key
                keys.append("QUIT")
                break
            for seq, key in ESC_SEQUENCES.items():
                if data.startswith(seq, i + 1):
                    keys.append(key)
                    i += 1 + len(seq)
                    break
            else:
                i += 1                      # unknown sequence, skip the ESC
            continue
        key = CHAR_KEYS.get(chr(b))
        if key:
            keys.append(key)
        i += 1
    return keys


def make_input():
    """Return (read_keys, restore). read_keys() gives a list of action names."""
    if os.name == "nt":
        import msvcrt
        # Extended keys arrive as a prefix byte followed by a code.
        extended = {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT",
                    "Q": "DROP", "R": "DROP", "G": "PAUSE", "O": "RESTART"}

        def read_keys():
            keys = []
            while msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):
                    key = extended.get(msvcrt.getwch())
                elif ch == "\x1b":
                    key = "QUIT"
                else:
                    key = CHAR_KEYS.get(ch)
                if key:
                    keys.append(key)
            return keys

        return read_keys, (lambda: None)

    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setcbreak(fd)

    def read_keys():
        keys = []
        while select.select([fd], [], [], 0)[0]:
            data = os.read(fd, 64)
            # A lone Esc must be told apart from the start of an arrow key,
            # so wait briefly for any follow-up bytes.
            if data == b"\x1b" and select.select([fd], [], [], 0.05)[0]:
                data += os.read(fd, 64)
            keys.extend(parse_keys(data))
        return keys

    def restore():
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    return read_keys, restore


# ---------------------------------------------------------------- sound ----

NOTE = {"A2": 110.0, "E2": 82.41, "A4": 440.0, "B4": 493.88,
        "C5": 523.25, "D5": 587.33, "E5": 659.26, "R": 0.0}
MELODY = [("E5", 1), ("B4", .5), ("C5", .5), ("D5", 1), ("C5", .5), ("B4", .5),
          ("A4", 1), ("A4", .5), ("C5", .5), ("E5", 1), ("D5", .5), ("C5", .5),
          ("B4", 1.5), ("C5", .5), ("D5", 1), ("E5", 1), ("C5", 1), ("A4", 1),
          ("A4", 1), ("R", 1)]


def build_theme(path, rate=22050, bpm=140):
    """Write a 16-beat square-wave loop (melody plus bass) to a WAV file."""
    beat = 60.0 / bpm
    beats = sum(b for _, b in MELODY)
    total = int(round(beats * beat * rate))
    mix = array.array("h", [0]) * total

    def square(freq, t):
        return 1.0 if (freq * t) % 1.0 < 0.5 else -1.0

    pos = 0
    for name, length in MELODY:
        n = int(round(length * beat * rate))
        freq = NOTE[name]
        if freq:
            for i in range(n):
                if pos + i < total:
                    env = 1.0 - 0.7 * i / n          # decaying note
                    mix[pos + i] += int(square(freq, i / rate) * 5000 * env)
        pos += n

    pos = 0
    n_beat = int(round(beat * rate))
    for k in range(int(round(beats))):
        freq = NOTE["A2"] if k % 2 == 0 else NOTE["E2"]
        for i in range(n_beat):
            if pos + i < total:
                mix[pos + i] += int(square(freq, i / rate) * 2500)
        pos += n_beat

    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(mix.tobytes())
    return path


class Music:
    """Loops the theme in the background using the system's audio player."""

    def __init__(self, path):
        self.path = path
        self.proc = None
        self.stopped = False
        self.winsound = None
        self.kind = None

    def start(self):
        if os.name == "nt":
            try:
                import winsound
                winsound.PlaySound(self.path, winsound.SND_FILENAME |
                                   winsound.SND_ASYNC | winsound.SND_LOOP)
                self.winsound = winsound
                self.kind = "winsound"
                return True
            except Exception:
                pass

        # (program, command, loops by itself)
        candidates = [
            ("ffplay", ["ffplay", "-nodisp", "-loglevel", "quiet", "-loop", "0"], True),
            ("mpv", ["mpv", "--no-video", "--really-quiet", "--loop-file=inf"], True),
            ("paplay", ["paplay"], False),
            ("aplay", ["aplay", "-q"], False),
            ("afplay", ["afplay"], False),
        ]
        for name, cmd, native_loop in candidates:
            if shutil.which(cmd[0]):
                self.kind = name
                threading.Thread(target=self._run, args=(cmd, native_loop),
                                 daemon=True).start()
                return True
        return False

    def _run(self, cmd, native_loop):
        while not self.stopped:
            started = time.monotonic()
            try:
                self.proc = subprocess.Popen(
                    cmd + [self.path], stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                return
            if self.stopped:
                self.proc.terminate()
                return
            rc = self.proc.wait()
            if native_loop or (rc != 0 and time.monotonic() - started < 1):
                return          # player finished for good, or it keeps failing

    def stop(self):
        self.stopped = True
        if self.winsound:
            self.winsound.PlaySound(None, 0)
        proc = self.proc
        if proc and proc.poll() is None:
            proc.terminate()


# ----------------------------------------------------------- game logic ----

def collides(board, shape, x, y):
    for r, row in enumerate(shape):
        for c, v in enumerate(row):
            if not v:
                continue
            nx, ny = x + c, y + r
            if nx < 0 or nx >= WIDTH or ny >= HEIGHT:
                return True
            if ny >= 0 and board[ny][nx]:
                return True
    return False


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None] * WIDTH for _ in range(HEIGHT)]
        self.bag = []
        self.score = 0
        self.lines = 0
        self.level = 1
        self.paused = False
        self.over = False
        self.confirm_restart = False
        self.fall_timer = 0.0
        self.next_kind = self._draw()
        self.spawn()

    def _draw(self):
        # 7-bag randomizer: every piece appears once per bag of seven
        if not self.bag:
            self.bag = list(SHAPES)
            random.shuffle(self.bag)
        return self.bag.pop()

    def spawn(self):
        self.kind = self.next_kind
        self.next_kind = self._draw()
        self.shape = [row[:] for row in SHAPES[self.kind]]
        self.x = (WIDTH - len(self.shape[0])) // 2
        self.y = 0
        if collides(self.board, self.shape, self.x, self.y):
            self.over = True

    def fall_interval(self):
        return max(0.05, 0.8 * (0.85 ** (self.level - 1)))

    def can_place(self, shape, x, y):
        return not collides(self.board, shape, x, y)

    def move(self, dx):
        if self.can_place(self.shape, self.x + dx, self.y):
            self.x += dx

    def rotate(self):
        new = [list(r) for r in zip(*self.shape[::-1])]  # clockwise
        for dx in (0, -1, 1, -2, 2):                     # simple wall kicks
            if self.can_place(new, self.x + dx, self.y):
                self.shape = new
                self.x += dx
                return

    def step_down(self):
        if self.can_place(self.shape, self.x, self.y + 1):
            self.y += 1
            return True
        self.lock()
        return False

    def soft_drop(self):
        if self.step_down():
            self.score += 1

    def hard_drop(self):
        dist = 0
        while self.can_place(self.shape, self.x, self.y + 1):
            self.y += 1
            dist += 1
        self.score += 2 * dist
        self.lock()

    def lock(self):
        for r, row in enumerate(self.shape):
            for c, v in enumerate(row):
                if v and self.y + r >= 0:
                    self.board[self.y + r][self.x + c] = self.kind
        self._clear_lines()
        self.spawn()

    def _clear_lines(self):
        remaining = [row for row in self.board if not all(row)]
        cleared = HEIGHT - len(remaining)
        if cleared:
            self.board = [[None] * WIDTH for _ in range(cleared)] + remaining
            self.lines += cleared
            self.score += LINE_POINTS[cleared] * self.level
            self.level = self.lines // 10 + 1

    def frozen(self):
        return self.paused or self.confirm_restart or self.over

    def handle(self, key):
        if self.confirm_restart:             # answer to the restart question
            self.confirm_restart = False
            if key == "RESTART":             # End pressed again: restart
                self.reset()
            return                           # any other key cancels
        if key == "RESTART":                 # first End press: ask first
            self.confirm_restart = True
            return
        if self.over:
            return
        if key == "PAUSE":
            self.paused = not self.paused
        elif self.paused:
            return
        elif key == "LEFT":
            self.move(-1)
        elif key == "RIGHT":
            self.move(1)
        elif key == "UP":
            self.rotate()
        elif key == "DOWN":
            self.soft_drop()
        elif key == "DROP":
            self.hard_drop()


# -------------------------------------------------------------- drawing ----

GHOST_CHARS = {"+": ".", "-": ".", "|": ":"}   # dotted version of the box edges


def edge_canvas(grid, frame):
    """Build the character canvas (and per-character piece kind) for a grid."""
    rows, cols = len(grid), len(grid[0])
    H, W = 2 * rows + 1, 3 * cols + 1
    ch = [[" "] * W for _ in range(H)]
    kd = [[None] * W for _ in range(H)]

    def cell(r, c):
        return grid[r][c] if 0 <= r < rows and 0 <= c < cols else None

    def h_edge(y, c):   # horizontal line on lattice row y, over column c
        above, below = cell(y - 1, c), cell(y, c)
        if (frame and y in (0, rows)) or above or below:
            return True, below or above
        return False, None

    def v_edge(r, x):   # vertical line on lattice column x, beside row r
        left, right = cell(r, x - 1), cell(r, x)
        if (frame and x in (0, cols)) or left or right:
            return True, right or left
        return False, None

    for y in range(rows + 1):
        for x in range(cols + 1):
            hits = [h_edge(y, x - 1), h_edge(y, x),
                    v_edge(y - 1, x), v_edge(y, x)]
            for ok, kind in hits:
                if ok:
                    ch[2 * y][3 * x] = "+"
                    kd[2 * y][3 * x] = kind
                    break
    for y in range(rows + 1):
        for c in range(cols):
            ok, kind = h_edge(y, c)
            if ok:
                for i in (1, 2):
                    ch[2 * y][3 * c + i] = "-"
                    kd[2 * y][3 * c + i] = kind
    for r in range(rows):
        for x in range(cols + 1):
            ok, kind = v_edge(r, x)
            if ok:
                ch[2 * r + 1][3 * x] = "|"
                kd[2 * r + 1][3 * x] = kind
    return ch, kd


def make_box(text_lines):
    """ASCII message box, e.g. +------+ / |PAUSED| / +------+."""
    inner = max(len(t) for t in text_lines) + 4
    top = "+" + "-" * inner + "+"
    body = ["|" + t.center(inner) + "|" for t in text_lines]
    return [top] + body + [top]


def render_grid(grid, frame, ghost=None, overlay=None):
    """
    Draw a grid of piece letters (or None) as ASCII boxes.
    Each cell is 3 columns x 2 lines: "+--" over "|  " (corners shared).
    Neighbouring cells share their border lines, so pieces look like blocks.
    frame=True draws an outer border around the whole grid.
    ghost: optional grid marking the landing spot; drawn as dotted gray boxes
    wherever the real pieces do not already draw a line.
    """
    ch, kd = edge_canvas(grid, frame)
    if ghost:
        gch, _ = edge_canvas(ghost, False)
        for r in range(len(ch)):
            for c in range(len(ch[0])):
                if ch[r][c] == " " and gch[r][c] != " ":
                    ch[r][c] = GHOST_CHARS[gch[r][c]]
                    kd[r][c] = "GHOST"

    if overlay:
        box = make_box(overlay)
        top = (len(ch) - len(box)) // 2
        left = (len(ch[0]) - len(box[0])) // 2
        for i, row in enumerate(box):
            for j, char in enumerate(row):
                ch[top + i][left + j] = char
                kd[top + i][left + j] = "MSG"

    lines = []
    for r in range(len(ch)):
        parts = []
        for c in range(len(ch[0])):
            k = kd[r][c]
            if k and not MONO:
                parts.append(f"\033[{COLORS[k]}m{ch[r][c]}\033[0m")
            else:
                parts.append(ch[r][c])
        lines.append("".join(parts))
    return lines


def ghost_grid(game):
    """Grid marking where the current piece would land on a hard drop."""
    if game.over:
        return None
    gy = game.y
    while game.can_place(game.shape, game.x, gy + 1):
        gy += 1
    grid = [[None] * WIDTH for _ in range(HEIGHT)]
    for r, row in enumerate(game.shape):
        for c, v in enumerate(row):
            if v and 0 <= gy + r < HEIGHT and 0 <= game.x + c < WIDTH:
                grid[gy + r][game.x + c] = "G"
    return grid


def board_with_piece(game):
    grid = [row[:] for row in game.board]
    if not game.over:
        for r, row in enumerate(game.shape):
            for c, v in enumerate(row):
                if v and 0 <= game.y + r < HEIGHT and 0 <= game.x + c < WIDTH:
                    grid[game.y + r][game.x + c] = game.kind
    return grid


def sidebar(game, preview_lines, sound_status):
    lines = ["TETRIS", "", "NEXT"] + preview_lines + [""]
    lines += [f"SCORE  {game.score}", f"LINES  {game.lines}",
              f"LEVEL  {game.level}", f"MUSIC  {sound_status}", ""]
    if game.over:
        lines += ["GAME OVER", "End restarts", "Esc quits", ""]
    lines += ["dotted = landing spot", ""]
    lines += ["CONTROLS", "<- ->       move", "up          rotate",
              "down        soft drop", "PgDn        hard drop",
              "Enter       hard drop", "Insert      hard drop",
              "Home        pause", "End         restart",
              "Esc/Ctrl+C  quit"]
    return lines


def draw(game, sound_status):
    overlay = None
    if game.confirm_restart:
        overlay = ["RESTART GAME?", "", "End again: yes", "Any other key: no"]
    elif game.paused:
        overlay = ["PAUSED", "", "Home: resume"]
    board_lines = render_grid(board_with_piece(game), frame=True,
                              ghost=ghost_grid(game), overlay=overlay)

    preview = [[None] * 4 for _ in range(4)]
    shape = SHAPES[game.next_kind]
    oy = (4 - len(shape)) // 2
    ox = (4 - len(shape[0])) // 2
    for r, row in enumerate(shape):
        for c, v in enumerate(row):
            if v:
                preview[oy + r][ox + c] = game.next_kind
    side = sidebar(game, render_grid(preview, frame=False), sound_status)

    out = []
    for i in range(max(len(board_lines), len(side))):
        left = board_lines[i] if i < len(board_lines) else ""
        right = side[i] if i < len(side) else ""
        out.append(left + "   " + right)

    sys.stdout.write("\033[H" + "\033[K\n".join(out) + "\033[K\033[J")
    sys.stdout.flush()


def install_player():
    """Install mpv with the system package manager. Returns True if it worked."""
    termux = "com.termux" in os.environ.get("PREFIX", "")
    if termux:
        steps = [["pkg", "install", "-y", "mpv"]]
    elif shutil.which("apt-get"):
        steps = [["apt-get", "update"], ["apt-get", "install", "-y", "mpv"]]
    elif shutil.which("dnf"):
        steps = [["dnf", "install", "-y", "mpv"]]
    elif shutil.which("pacman"):
        steps = [["pacman", "-Sy", "--noconfirm", "mpv"]]
    elif shutil.which("zypper"):
        steps = [["zypper", "--non-interactive", "install", "mpv"]]
    elif shutil.which("apk"):
        steps = [["apk", "add", "mpv"]]
    else:
        return False

    needs_root = not termux and hasattr(os, "geteuid") and os.geteuid() != 0
    if needs_root:
        if not shutil.which("sudo"):
            return False
        steps = [["sudo"] + s for s in steps]

    for cmd in steps:
        try:
            subprocess.run(cmd, check=True)
        except (subprocess.CalledProcessError, OSError):
            return False
    return shutil.which("mpv") is not None


def offer_install():
    """Ask once, then install mpv if no audio player is available."""
    if not sys.stdin.isatty():
        return False
    try:
        answer = input("No audio player found. Install mpv so the music plays? [Y/n] ")
    except (EOFError, KeyboardInterrupt):
        return False
    if answer.strip().lower() not in ("", "y", "yes"):
        return False
    print("Installing mpv...")
    ok = install_player()
    print("mpv installed." if ok else "Could not install mpv; continuing without music.")
    time.sleep(1.5)
    return ok


# ------------------------------------------------------------------ main ----

def main():
    if os.name == "nt":
        os.system("")  # turns on ANSI escape codes in older Windows consoles

    theme = os.path.join(tempfile.gettempdir(), "ascii_tetris_theme.wav")
    music = None
    if NO_SOUND:
        sound_status = "off (flag)"
    else:
        try:
            build_theme(theme)
            music = Music(theme)
            started = music.start()
            if not started and offer_install():
                started = music.start()
            sound_status = f"on ({music.kind})" if started else "off (no player)"
        except Exception:
            music = None
            sound_status = "off (error)"

    read_keys, restore = make_input()
    game = Game()
    out = sys.stdout
    out.write("\033[?25l\033[2J")   # hide cursor, clear screen
    out.flush()
    last = time.monotonic()
    try:
        while True:
            for key in read_keys():
                if key == "QUIT":
                    return
                game.handle(key)

            now = time.monotonic()
            if not game.frozen():
                game.fall_timer += now - last
                if game.fall_timer >= game.fall_interval():
                    game.fall_timer = 0.0
                    game.step_down()
            last = now

            draw(game, sound_status)
            time.sleep(1 / 30)
    except KeyboardInterrupt:
        pass
    finally:
        restore()
        if music:
            music.stop()
        try:
            os.remove(theme)
        except OSError:
            pass
        out.write("\033[0m\033[?25h\n")
        out.flush()


if __name__ == "__main__":
    main()
