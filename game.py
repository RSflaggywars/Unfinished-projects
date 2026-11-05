"""Unfinished projects - a small cat golf game.
A love letter to unfinished things. Built with tkinter, zero dependencies.
"""

import math
import random
import tkinter as tk

W, H = 960, 680
BG = "#140b26"
COURT = "#241543"
COURT_DARK = "#1d1138"
LINE = "#8f7bd8"
CAT = "#ff9f43"
CAT_DARK = "#7a3c00"
BALL = "#f5f0ff"
HOLE = "#05030c"

FRICTION = 0.985
MAX_POWER = 22.0
BALL_R = 8
SINK_DELAY = 110  # frames the "SUNK!" banner stays up

# Each hole: name, cat, ball, hole, par, walls[(x,y,w,h)], bumps[(x,y,r)]
LEVELS = [
    dict(name="the beginning",
         cat=(90, 340), ball=(150, 340), hole=(860, 340), par=3,
         walls=[], bumps=[]),
    dict(name="the hallway",
         cat=(80, 110), ball=(150, 110), hole=(860, 560), par=4,
         walls=[(430, 60, 26, 320), (430, 400, 26, 220)],
         bumps=[(300, 430, 42), (620, 150, 42)]),
    dict(name="the spiral",
         cat=(80, 570), ball=(150, 570), hole=(870, 90), par=5,
         walls=[(210, 210, 26, 360), (470, 60, 26, 320), (720, 320, 26, 300)],
         bumps=[(360, 500, 46), (580, 210, 36), (780, 540, 30)]),
]

MOTE_COLORS = ["#8f7bd8", "#ffd166", "#7ee787", "#ff7b72", "#79c0ff"]
CONFETTI_COLORS = ["#ffd166", "#ff7b72", "#7ee787", "#79c0ff", "#ff9f43",
                   "#c084fc", "#f5f0ff"]


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Unfinished projects")
        self.cv = tk.Canvas(root, width=W, height=H, bg=BG,
                            highlightthickness=0)
        self.cv.pack()

        self.level = 0
        self.strokes = 0
        self.total_strokes = 0
        self.aiming = False
        self.end_game = False
        self.trail = []
        self.confetti = []
        self.sink_timer = 0
        self.shot_line = None
        self.dots = None
        self.power_bar = None
        self.t = 0

        # ambient drifting motes
        self.motes = [
            {"x": random.uniform(0, W), "y": random.uniform(0, H),
             "vx": random.uniform(-0.15, 0.15),
             "vy": random.uniform(-0.1, -0.25),
             "r": random.uniform(1.5, 3.5),
             "c": random.choice(MOTE_COLORS)}
            for _ in range(28)
        ]

        self.cv.bind("<ButtonPress-1>", self.press)
        self.cv.bind("<B1-Motion>", self.drag_move)
        self.cv.bind("<ButtonRelease-1>", self.release)
        root.bind("<r>", self.on_r)
        root.bind("<n>", self.on_n)
        root.focus_set()

        self.load_level()
        self.tick()

    # ---------- level setup ----------

    def load_level(self):
        lv = LEVELS[self.level]
        self.cat = list(lv["cat"])
        self.ball = list(lv["ball"])
        self.ball_vel = [0.0, 0.0]
        self.hole = lv["hole"]
        self.walls = lv["walls"]
        self.bumps = lv["bumps"]
        self.par = lv["par"]
        self.strokes = 0
        self.trail = []
        self.confetti = []
        self.aiming = False
        self.end_game = False
        self.sink_timer = 0
        self.clear_aim_items()
        self.redraw()

    def clear_aim_items(self):
        for attr in ("shot_line", "dots", "power_bar"):
            item = getattr(self, attr, None)
            if item:
                self.cv.delete(item)
                setattr(self, attr, None)

    def reset_hole(self):
        self.ball = list(LEVELS[self.level]["ball"])
        self.ball_vel = [0.0, 0.0]
        self.strokes = 0
        self.trail = []
        self.clear_aim_items()
        self.aiming = False
        self.sink_timer = 0
        self.redraw()

    def full_reset(self):
        self.level = 0
        self.total_strokes = 0
        self.load_level()

    def on_r(self, _e):
        if self.end_game:
            self.full_reset()
        else:
            self.reset_hole()

    def on_n(self, _e):
        if self.end_game:
            self.full_reset()
        elif self.sink_timer == 0 and self.level + 1 < len(LEVELS):
            self.level += 1
            self.load_level()

    # ---------- input ----------

    def aim_power(self, e):
        bx, by = self.ball
        dx, dy = bx - e.x, by - e.y
        d = math.hypot(dx, dy)
        power = min(d / 30.0, MAX_POWER)
        ux, uy = (dx / d, dy / d) if d else (0, 0)
        return power, ux, uy

    def press(self, e):
        if self.aiming or self.sink_timer > 0 or self.end_game:
            return
        bx, by = self.ball
        if math.hypot(e.x - bx, e.y - by) < 70 and self.speed() < 0.1:
            self.aiming = True
            self.shot_line = self.cv.create_line(
                bx, by, e.x, e.y, fill="#ffd166", width=3,
                dash=(6, 4), capstyle="round")
            self.dots = self.cv.create_line(bx, by, bx, by,
                                            fill="#ffd166", width=5,
                                            smooth=True)
            self.power_bar = self.cv.create_rectangle(
                20, H - 46, 20, H - 26, fill="#7ee787", outline=LINE)

    def drag_move(self, e):
        if not self.aiming:
            return
        bx, by = self.ball
        power, ux, uy = self.aim_power(e)
        self.cv.coords(self.shot_line, bx, by, e.x, e.y)

        pts = []
        for i in range(1, 7):
            px = bx + ux * power * 16 * i
            py = by + uy * power * 16 * i
            if 0 <= px <= W and 0 <= py <= H:
                pts += [px, py]
        self.cv.coords(self.dots, bx, by, *(pts or [bx, by]))

        frac = power / MAX_POWER
        color = "#7ee787" if frac < 0.5 else ("#ffd166" if frac < 0.8
                                              else "#ff7b72")
        self.cv.coords(self.power_bar, 20, H - 46,
                       20 + 220 * frac, H - 26)
        self.cv.itemconfigure(self.power_bar, fill=color)

    def release(self, e):
        if not self.aiming:
            return
        self.aiming = False
        power, ux, uy = self.aim_power(e)
        self.clear_aim_items()
        if power * 30 < 8:
            return
        self.ball_vel = [ux * power, uy * power]
        self.strokes += 1
        self.trail = []
        self.redraw()

    def speed(self):
        return math.hypot(*self.ball_vel)

    # ---------- physics ----------

    def bounce(self, nx, ny, rest):
        dot = self.ball_vel[0] * nx + self.ball_vel[1] * ny
        if dot < 0:
            self.ball_vel[0] -= 2 * dot * nx
            self.ball_vel[1] -= 2 * dot * ny
            self.ball_vel[0] *= rest
            self.ball_vel[1] *= rest

    def step(self):
        if self.speed() < 0.05:
            self.ball_vel = [0.0, 0.0]
            return False
        self.ball[0] += self.ball_vel[0]
        self.ball[1] += self.ball_vel[1]
        self.ball_vel[0] *= FRICTION
        self.ball_vel[1] *= FRICTION
        self.trail.append((self.ball[0], self.ball[1]))
        if len(self.trail) > 14:
            self.trail.pop(0)

        r = BALL_R
        if self.ball[0] < r:
            self.ball[0] = r
            self.ball_vel[0] = abs(self.ball_vel[0]) * 0.8
        if self.ball[0] > W - r:
            self.ball[0] = W - r
            self.ball_vel[0] = -abs(self.ball_vel[0]) * 0.8
        if self.ball[1] < r:
            self.ball[1] = r
            self.ball_vel[1] = abs(self.ball_vel[1]) * 0.8
        if self.ball[1] > H - r:
            self.ball[1] = H - r
            self.ball_vel[1] = -abs(self.ball_vel[1]) * 0.8

        for wx, wy, ww, wh in self.walls:
            cx = min(max(self.ball[0], wx), wx + ww)
            cy = min(max(self.ball[1], wy), wy + wh)
            ddx, ddy = self.ball[0] - cx, self.ball[1] - cy
            dist = math.hypot(ddx, ddy)
            if 0 < dist < r:
                nx, ny = ddx / dist, ddy / dist
                self.ball[0] = cx + nx * r
                self.ball[1] = cy + ny * r
                self.bounce(nx, ny, 0.85)

        for bx2, by2, br in self.bumps:
            ddx, ddy = self.ball[0] - bx2, self.ball[1] - by2
            dist = math.hypot(ddx, ddy)
            min_d = r + br
            if 0 < dist < min_d:
                nx, ny = ddx / dist, ddy / dist
                self.ball[0] = bx2 + nx * min_d
                self.ball[1] = by2 + ny * min_d
                self.bounce(nx, ny, 0.9)

        if (math.hypot(self.ball[0] - self.hole[0],
                       self.ball[1] - self.hole[1]) < 17
                and self.speed() < 6):
            return True
        return False

    # ---------- particles ----------

    def spawn_confetti(self):
        hx, hy = self.hole
        for _ in range(90):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(1, 5)
            self.confetti.append({
                "x": hx, "y": hy,
                "vx": math.cos(ang) * sp,
                "vy": math.sin(ang) * sp - 1.5,
                "life": random.uniform(50, 110),
                "c": random.choice(CONFETTI_COLORS),
                "s": random.uniform(2, 5),
            })

    def update_particles(self):
        for m in self.motes:
            m["x"] += m["vx"]
            m["y"] += m["vy"]
            if m["y"] < -5:
                m["y"] = H + 5
                m["x"] = random.uniform(0, W)
            if m["x"] < -5:
                m["x"] = W + 5
            elif m["x"] > W + 5:
                m["x"] = -5

        for p in self.confetti:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.08
            p["vx"] *= 0.99
            p["life"] -= 1
        self.confetti = [p for p in self.confetti if p["life"] > 0]

    # ---------- drawing ----------

    def draw_cat(self, cx, cy):
        wag = math.sin(self.t * 0.006) * 8
        # tail
        self.cv.create_line(cx - 10, cy + 8, cx - 26, cy + 16 + wag,
                            cx - 34, cy + 6 + wag, fill=CAT_DARK, width=4,
                            smooth=True, tags="scene")
        # body
        self.cv.create_oval(cx - 15, cy - 9, cx + 15, cy + 15,
                            fill=CAT, outline=CAT_DARK, width=2, tags="scene")
        # belly
        self.cv.create_oval(cx - 8, cy + 2, cx + 8, cy + 12,
                            fill="#ffc98a", outline="", tags="scene")
        # ears
        self.cv.create_polygon(cx - 13, cy - 8, cx - 7, cy - 24,
                               cx, cy - 10, fill=CAT,
                               outline=CAT_DARK, width=2, tags="scene")
        self.cv.create_polygon(cx - 10, cy - 12, cx - 7, cy - 20,
                               cx - 4, cy - 12, fill="#ffb86b",
                               tags="scene")
        self.cv.create_polygon(cx + 2, cy - 10, cx + 8, cy - 23,
                               cx + 15, cy - 7, fill=CAT,
                               outline=CAT_DARK, width=2, tags="scene")
        self.cv.create_polygon(cx + 5, cy - 12, cx + 8, cy - 19,
                               cx + 11, cy - 11, fill="#ffb86b",
                               tags="scene")
        # eyes look toward the ball
        bx, by = self.ball
        look = max(-2, min(2, (bx - cx) / 60))
        looky = max(-1.5, min(1.5, (by - cy) / 60))
        for ex in (-5, 6):
            exx = cx + ex + look
            eyy = cy - 4 + looky
            self.cv.create_oval(exx - 3, eyy - 3, exx + 3, eyy + 3,
                                fill="#fff", outline=CAT_DARK, tags="scene")
            self.cv.create_oval(exx - 1.2, eyy - 1.2, exx + 1.2, eyy + 1.2,
                                fill="#1a1030", tags="scene")
        # nose, whiskers, mouth
        self.cv.create_polygon(cx - 2, cy + 1, cx + 2, cy + 1, cx, cy + 4,
                               fill="#ff7b72", outline=CAT_DARK, tags="scene")
        for s in (-1, 1):
            self.cv.create_line(cx + s * 4, cy + 4, cx + s * 16, cy + 2 + s,
                                fill="#fff", width=1, tags="scene")
            self.cv.create_line(cx + s * 4, cy + 6, cx + s * 16, cy + 8 - s,
                                fill="#fff", width=1, tags="scene")
        self.cv.create_arc(cx - 4, cy + 4, cx + 4, cy + 9,
                           start=20, extent=140, style="arc",
                           outline=CAT_DARK, width=1, tags="scene")

    def draw_end(self):
        self.cv.create_rectangle(0, 0, W, H, fill=BG, tags="scene")
        for p in self.confetti:
            self.cv.create_rectangle(p["x"], p["y"],
                                     p["x"] + p["s"], p["y"] + p["s"] * 0.6,
                                     fill=p["c"], outline="", tags="scene")
        msg = (f"You finished all {len(LEVELS)} holes.\n\n"
               f"Total strokes: {self.total_strokes}\n\n"
               "Some projects stay unfinished.\n"
               "This one, at least, got a hole in one.\n\n"
               "press R or N to play again")
        self.cv.create_text(W / 2, H / 2, text=msg, fill="#ffd166",
                            font=("Consolas", 20), justify="center",
                            tags="scene")

    def redraw(self):
        self.cv.delete("scene")

        if self.end_game:
            self.draw_end()
            return

        # court with subtle checker
        self.cv.create_rectangle(0, 0, W, H, fill=COURT_DARK, tags="scene")
        tile = 60
        for y in range(0, H, tile):
            for x in range(0, W, tile):
                if (x // tile + y // tile) % 2 == 0:
                    self.cv.create_rectangle(x, y, x + tile, y + tile,
                                             fill=COURT, outline="",
                                             tags="scene")
        # vignette border
        self.cv.create_rectangle(4, 4, W - 4, H - 4, outline=LINE,
                                 width=2, tags="scene")
        self.cv.create_rectangle(10, 10, W - 10, H - 10, outline="#3a2560",
                                 width=1, tags="scene")

        # ambient motes
        for m in self.motes:
            self.cv.create_oval(m["x"] - m["r"], m["y"] - m["r"],
                                m["x"] + m["r"], m["y"] + m["r"],
                                fill=m["c"], outline="", tags="scene")

        # walls - brick-ish
        for wx, wy, ww, wh in self.walls:
            self.cv.create_rectangle(wx, wy, wx + ww, wy + wh,
                                     fill="#3d2566", outline=LINE, width=2,
                                     tags="scene")
            step = 26
            for i in range(1, int(ww / step) + 1):
                self.cv.create_line(wx + i * step, wy, wx + i * step,
                                    wy + wh, fill="#2c1a4d", width=1,
                                    tags="scene")
            for j in range(1, int(wh / step) + 1):
                off = step / 2 if j % 2 else 0
                self.cv.create_line(wx + off, wy + j * step,
                                    min(wx + ww, wx + off + step),
                                    wy + j * step,
                                    fill="#2c1a4d", width=1, tags="scene")

        # bumps - striped circles
        for bx2, by2, br in self.bumps:
            self.cv.create_oval(bx2 - br, by2 - br, bx2 + br, by2 + br,
                                fill="#553180", outline=LINE, width=2,
                                tags="scene")
            for k in range(-2, 3):
                self.cv.create_line(bx2 + k * br * 0.5 - br * 0.2,
                                    by2 - br, bx2 + k * br * 0.5 - br * 0.2,
                                    by2 + br, fill="#3d2566", width=3,
                                    tags="scene")
            self.cv.create_oval(bx2 - 6, by2 - 6, bx2 + 6, by2 + 6,
                                fill="#7a5cc9", outline=LINE, tags="scene")

        # hole + waving flag
        hx, hy = self.hole
        self.cv.create_oval(hx - 17, hy - 17, hx + 17, hy + 17,
                            fill=HOLE, outline="#000", width=3, tags="scene")
        self.cv.create_oval(hx - 8, hy - 8, hx + 8, hy + 8,
                            fill="#000", tags="scene")
        self.cv.create_oval(hx - 3, hy - 3, hx + 3, hy + 3,
                            fill="#1a1030", tags="scene")
        wave = math.sin(self.t * 0.008) * 4
        self.cv.create_line(hx, hy - 17, hx, hy - 52, fill="#cbb8ff",
                            width=3, tags="scene")
        self.cv.create_polygon(hx, hy - 52, hx + 24, hy - 46 + wave,
                               hx, hy - 40, fill="#ff7b72",
                               outline="#7a1f1f", tags="scene")

        # ball trail
        for i, (tx, ty) in enumerate(self.trail):
            frac = i / max(len(self.trail), 1)
            rr = BALL_R * (0.4 + 0.6 * frac)
            shade = "#8f7bd8" if frac < 0.5 else "#5b3d99"
            self.cv.create_oval(tx - rr, ty - rr, tx + rr, ty + rr,
                                fill=shade, outline="", tags="scene")

        # ball with shadow and highlight
        bx, by = self.ball
        self.cv.create_oval(bx - BALL_R - 1, by - BALL_R + 1,
                            bx + BALL_R - 3, by + BALL_R + 3,
                            fill="#3a2560", outline="", tags="scene")
        self.cv.create_oval(bx - BALL_R, by - BALL_R, bx + BALL_R, by + BALL_R,
                            fill=BALL, outline="#999", width=1, tags="scene")
        self.cv.create_oval(bx - BALL_R * 0.5, by - BALL_R * 0.6,
                            bx - BALL_R * 0.1, by - BALL_R * 0.2,
                            fill="#ffffff", outline="", tags="scene")

        # confetti
        for p in self.confetti:
            self.cv.create_rectangle(p["x"], p["y"],
                                     p["x"] + p["s"], p["y"] + p["s"] * 0.6,
                                     fill=p["c"], outline="", tags="scene")

        # cat
        self.draw_cat(*self.cat)

        # tee marker
        sx, sy = LEVELS[self.level]["ball"]
        self.cv.create_text(sx, sy - 22, text="tee", fill="#8f7bd8",
                            font=("Consolas", 9, "italic"), tags="scene")

        # HUD
        lv = LEVELS[self.level]
        self.cv.create_text(20, 20, anchor="w",
                            text="Unfinished projects",
                            fill="#cbb8ff", font=("Consolas", 15, "bold"),
                            tags="scene")
        self.cv.create_text(20, 42, anchor="w",
                            text=f"hole {self.level + 1}/{len(LEVELS)}  ·  "
                                 f"\"{lv['name']}\"  ·  par {lv['par']}  ·  "
                                 f"strokes {self.strokes}",
                            fill="#9d8bd0", font=("Consolas", 11),
                            tags="scene")
        self.cv.create_text(W - 20, 20, anchor="e",
                            text="drag near the ball to shoot   ·   R reset   ·"
                                 "   N skip",
                            fill="#8f7bd8", font=("Consolas", 11),
                            tags="scene")
        self.cv.create_text(W / 2, H - 16,
                            text="some projects stay unfinished — this one "
                                 "at least got a hole in one",
                            fill="#5b4a8a", font=("Consolas", 10, "italic"),
                            tags="scene")

        # sink banner
        if self.sink_timer > 0:
            frac = self.strokes / max(self.par, 1)
            verdict = ("hole in one!!" if self.strokes == 1
                       else "under par!" if frac <= 0.75
                       else "par" if frac <= 1.0
                       else "over par...")
            color = "#7ee787" if frac <= 1.0 else "#ff7b72"
            self.cv.create_text(W / 2, H / 2 - 40,
                                text="SUNK!", fill="#ffd166",
                                font=("Consolas", 42, "bold"), tags="scene")
            self.cv.create_text(W / 2, H / 2 + 10,
                                text=f"{self.strokes} strokes  ·  {verdict}",
                                fill=color, font=("Consolas", 20, "bold"),
                                tags="scene")
            hint = ("press N for the next hole" if self.level + 1 <
                    len(LEVELS) else "press R or N to finish")
            self.cv.create_text(W / 2, H / 2 + 44, text=hint,
                                fill="#8f7bd8", font=("Consolas", 13),
                                tags="scene")

    # ---------- main loop ----------

    def tick(self):
        self.t += 1
        self.update_particles()

        if self.sink_timer > 0:
            self.sink_timer -= 1
            if self.sink_timer == 0 and self.level + 1 >= len(LEVELS):
                self.end_game = True
                for _ in range(140):
                    self.confetti.append({
                        "x": random.uniform(0, W), "y": random.uniform(-H, 0),
                        "vx": random.uniform(-0.5, 0.5),
                        "vy": random.uniform(0.5, 2),
                        "life": random.uniform(200, 400),
                        "c": random.choice(CONFETTI_COLORS),
                        "s": random.uniform(2, 5),
                    })
        elif not self.end_game:
            sunk = self.step()
            if sunk:
                self.total_strokes += self.strokes
                self.spawn_confetti()
                self.sink_timer = SINK_DELAY
                self.ball_vel = [0.0, 0.0]

        self.redraw()
        self.root.after(16, self.tick)


def main():
    root = tk.Tk()
    root.resizable(False, False)
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()
