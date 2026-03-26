import urllib.request
import numpy as np
import tkinter as tk
from tkinter import font as tkfont
import socket, threading, time, math
from PIL import Image, ImageTk
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# ── CONFIG ────────────────────────────────────────────────────────────────────
RDK_IP = "172.20.10.2"
PORT   = 5000

# ── PALETTE ───────────────────────────────────────────────────────────────────
BG          = "#080b10"
PANEL       = "#0e1118"
BORDER      = "#1a2438"
ACCENT_B    = "#00c8ff"
ACCENT_N    = "#00ff9d"
ACCENT_V    = "#ff6b35"
TEXT_DIM    = "#304050"
TEXT_MID    = "#5a7898"
TEXT_BRIGHT = "#c8dff0"
KEY_BG      = "#111828"
KEY_IDLE    = "#1e2e48"
DANGER      = "#ff3060"
GOLD        = "#ffbe40"
CAM_BG      = "#050708"
CAM_BORDER  = "#0f1e30"
LEFT_CLR    = ACCENT_N
RIGHT_CLR   = "#ff4455"

MODE_ACCENTS = {"B": ACCENT_B, "N": ACCENT_N, "V": ACCENT_V}
MODE_NAMES   = {"B": "BODY",   "N": "HANDS",  "V": "ARMS"}


# ── CONTROLLER ────────────────────────────────────────────────────────────────
class RDKController:
    SEND_INTERVAL = 0.05   # 50 ms between repeat sends while key held

    def __init__(self):
        self.sock = None
        self.connected = False
        self.mode = "B"
        self._pending_cmd = None
        self._lock = threading.Lock()
        threading.Thread(target=self._send_loop, daemon=True).start()

    def _send_loop(self):
        while True:
            time.sleep(self.SEND_INTERVAL)
            with self._lock:
                cmd = self._pending_cmd
                # Keep _pending_cmd set so next tick resends while key is held
            if cmd is None:
                continue
            self._raw_send(cmd)

    def _raw_send(self, cmd):
        if not self.connected or not self.sock:
            return False
        try:
            self.sock.sendall((cmd + "\n").encode())
            return True
        except Exception:
            self.connected = False
            self.sock = None
            return False

    def send(self, cmd):
        """Queue a command to be sent repeatedly while held."""
        if not self.connected:
            return False
        with self._lock:
            self._pending_cmd = cmd
        # Also fire immediately so there's no initial delay
        return self._raw_send(cmd)

    def send_immediate(self, cmd):
        """Send once right now and clear the repeat queue."""
        with self._lock:
            self._pending_cmd = None
        return self._raw_send(cmd)

    def clear_pending(self):
        """Call on key-release to stop the repeat loop."""
        with self._lock:
            self._pending_cmd = None

    def connect(self, ip=RDK_IP, port=PORT):
        try:
            if self.sock:
                try: self.sock.close()
                except: pass
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024)
            self.sock.settimeout(5)
            self.sock.connect((ip, port))
            self.sock.settimeout(None)
            self.connected = True
            return True, None
        except Exception as e:
            self.sock = None
            self.connected = False
            return False, str(e)

    def disconnect(self):
        with self._lock:
            self._pending_cmd = None
        if self.sock:
            try:
                self.sock.sendall(b"END\n")
                self.sock.close()
            except: pass
            self.sock = None
        self.connected = False


# ── DRAWING HELPERS ───────────────────────────────────────────────────────────
def _fs(S, base):
    return max(7, int(base * S))

def _grid(canvas, w, h):
    step = max(32, min(w, h) // 12)
    for i in range(0, w, step):
        canvas.create_line(i, 0, i, h, fill="#0a1018", width=1)
    for i in range(0, h, step):
        canvas.create_line(0, i, w, i, fill="#0a1018", width=1)

def _circle_btn(canvas, cx, cy, r, glyph, key, active, acc, fs_big, fs_sm):
    rim  = acc  if active else KEY_IDLE
    fill = acc  if active else KEY_BG
    fg   = BG   if active else TEXT_BRIGHT
    dim  = BG   if active else TEXT_DIM
    canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill=fill, outline=rim,
                       width=max(1, int(r * 0.09)))
    canvas.create_text(cx, cy - int(r * 0.16), text=glyph,
                       font=("Courier New", fs_big, "bold"), fill=fg)
    canvas.create_text(cx, cy + int(r * 0.44), text=key,
                       font=("Courier New", fs_sm, "bold"), fill=dim)

def _badge(canvas, cx, cy, bw, bh, sign, key, active, clr, fs_s, fs_k):
    bg = clr if active else KEY_BG
    fg = BG  if active else clr
    canvas.create_rectangle(cx-bw, cy-bh, cx+bw, cy+bh,
                             fill=bg, outline=clr, width=1)
    canvas.create_text(cx - bw * 0.30, cy, text=sign,
                       font=("Courier New", fs_s, "bold"),
                       fill=TEXT_BRIGHT if active else TEXT_DIM)
    canvas.create_text(cx + bw * 0.32, cy, text=key,
                       font=("Courier New", fs_k, "bold"), fill=fg)


# ═════════════════════════════════════════════════════════════════════════════
#  BODY MODE
# ═════════════════════════════════════════════════════════════════════════════
def draw_body_left(canvas, w, h, acc, pressed):
    canvas.delete("all")
    _grid(canvas, w, h)
    S = min(w / 320.0, h / 500.0)
    def s(v): return int(v * S)
    cx = w // 2

    ry = int(h * 0.27)
    for wx in [-s(48), s(48)]:
        canvas.create_oval(cx+wx-s(22), ry+s(16), cx+wx+s(22), ry+s(62),
                           fill="#0c1824", outline=acc, width=max(1,s(2)))
        canvas.create_oval(cx+wx-s(7), ry+s(32), cx+wx+s(7), ry+s(46),
                           fill=acc, outline="")
    canvas.create_line(cx-s(48), ry+s(39), cx+s(48), ry+s(39),
                       fill=acc, width=max(1,s(2)))
    canvas.create_rectangle(cx-s(34), ry-s(46), cx+s(34), ry+s(18),
                             fill="#0d1a2c", outline=acc, width=max(1,s(2)))
    canvas.create_rectangle(cx-s(20), ry-s(34), cx+s(20), ry-s(7),
                             fill="#08101e", outline=BORDER, width=1)
    canvas.create_oval(cx-s(7), ry-s(28), cx+s(7), ry-s(13), fill=acc)
    canvas.create_rectangle(cx-s(7), ry-s(56), cx+s(7), ry-s(46),
                             fill="#0d1a2c", outline=acc, width=1)
    canvas.create_oval(cx-s(24), ry-s(88), cx+s(24), ry-s(56),
                       fill="#0d1a2c", outline=acc, width=max(1,s(2)))
    canvas.create_oval(cx-s(12), ry-s(80), cx-s(4), ry-s(70), fill=acc)
    canvas.create_oval(cx+s(4),  ry-s(80), cx+s(12), ry-s(70), fill=acc)
    canvas.create_rectangle(cx-s(16), ry-s(75), cx+s(16), ry-s(69),
                             fill=acc, outline="", stipple="gray50")

    r   = s(30)
    gap = s(74)
    bcy = int(h * 0.77)
    canvas.create_text(cx, bcy - gap - r - s(14), text="MOVEMENT",
                       font=("Courier New", _fs(S,11), "bold"), fill=TEXT_DIM)
    for ax, ay, key, gl in [
        (cx,     bcy-gap, "W", "↑"),
        (cx,     bcy+r,   "S", "↓"),
        (cx-gap, bcy,     "A", "←"),
        (cx+gap, bcy,     "D", "→"),
    ]:
        _circle_btn(canvas, ax, ay, r, gl, key,
                    key.lower() in pressed, acc, _fs(S,18), _fs(S,11))


def draw_body_right(canvas, w, h, acc, pressed, speed_level):
    canvas.delete("all")
    _grid(canvas, w, h)
    S = min(w / 320.0, h / 500.0)
    def s(v): return int(v * S)
    cx = w // 2

    r   = s(28)
    gap = s(66)
    hcy = int(h * 0.27)
    canvas.create_text(cx, hcy - gap - r - s(14), text="HEAD",
                       font=("Courier New", _fs(S,11), "bold"), fill=GOLD)
    for ax, ay, key, gl in [
        (cx,     hcy-gap, "I", "↑"),
        (cx,     hcy+r,   "K", "↓"),
        (cx-gap, hcy,     "J", "←"),
        (cx+gap, hcy,     "L", "→"),
    ]:
        _circle_btn(canvas, ax, ay, r, gl, key,
                    key.lower() in pressed, GOLD, _fs(S,16), _fs(S,10))

    bar_defs = [
        ("0","STOP","#1a3040"),
        ("1","SLOW","#1a4a68"),
        ("2","MED", "#006890"),
        ("3","FAST", acc),
    ]
    bx0    = int(w * 0.10);  bx1    = int(w * 0.90)
    sy_bot = int(h * 0.95);  sy_top = int(h * 0.60)
    total_h = sy_bot - sy_top
    bar_h   = int(total_h * 0.18)
    bar_gap = int(total_h * 0.06)
    canvas.create_text(cx, sy_top - s(16), text="SPEED",
                       font=("Courier New", _fs(S,11), "bold"), fill=TEXT_DIM)
    for i, (k, lbl, clr) in enumerate(bar_defs):
        by_bot = sy_bot - i * (bar_h + bar_gap)
        by_top = by_bot - bar_h
        bcy2   = (by_top + by_bot) // 2
        active = (speed_level >= i);  is_cur = (speed_level == i)
        fill = clr if active else "#0c1624"
        canvas.create_rectangle(bx0, by_top, bx1, by_bot,
                                 fill=fill, outline=clr if active else BORDER, width=1)
        canvas.create_text(bx0+s(20), bcy2, text=k,
                           font=("Courier New", _fs(S,13), "bold"),
                           fill=BG if active else TEXT_DIM)
        canvas.create_text(bx1-s(10), bcy2, text=lbl,
                           font=("Courier New", _fs(S,10), "bold"),
                           fill=BG if active else TEXT_DIM, anchor="e")
        if is_cur:
            canvas.create_text(bx0-s(8), bcy2, text="▶",
                               font=("Courier New", _fs(S,10), "bold"),
                               fill=acc, anchor="e")
        if active:
            canvas.create_rectangle(bx0, by_top, bx0+s(4), by_bot,
                                     fill=clr, outline="")


#  HAND MODE
def draw_hand(canvas, w, h, side, pressed):
    canvas.delete("all")
    _grid(canvas, w, h)

    clr   = LEFT_CLR if side == "L" else RIGHT_CLR
    S     = min(w / 300.0, h / 560.0)
    def s(v): return int(v * S)
    cx    = w // 2
    tsign = 1 if side == "L" else -1

    bw    = s(20)
    bh    = s(11)
    bstep = bh*2 + s(4)
    lbl_gap = s(18)
    fs_s  = _fs(S, 10)
    fs_k  = _fs(S,  8)
    fs_l  = _fs(S,  8)

    def _stack(lx, ly, k_in, k_out):
        in_a  = k_in.lower()  in pressed
        out_a = k_out.lower() in pressed
        _badge(canvas, lx, ly - bstep,      bw, bh, "+", k_out, out_a, clr, fs_s, fs_k)
        _badge(canvas, lx, ly - bstep * 2,  bw, bh, "−", k_in,  in_a,  clr, fs_s, fs_k)

    py      = int(h * 0.58)
    pw      = s(98)
    ph      = s(96)
    wrist_w = int(pw * 0.70)
    knuck_y = py - ph // 2
    wrist_y = py + ph // 2

    palm_pts = [
        cx - pw//2 + s(6), knuck_y,
        cx + pw//2 - s(6), knuck_y,
        cx + wrist_w//2,   wrist_y,
        cx - wrist_w//2,   wrist_y,
    ]
    canvas.create_polygon(palm_pts, fill="#0e1e34", outline=clr, width=max(1,s(2)))
    for frac, dash in [(0.28,(6,4)), (0.54,(4,4)), (0.76,(3,5))]:
        yc = int(knuck_y + ph * frac)
        xo = int(pw * (1-frac) * 0.10)
        canvas.create_line(cx - pw//2 + xo + s(4), yc,
                           cx + pw//2 - xo - s(4), yc,
                           fill="#162840", width=1, dash=dash)

    canvas.create_rectangle(cx - wrist_w//2, wrist_y,
                             cx + wrist_w//2, wrist_y + s(26),
                             fill="#0b1628", outline=clr, width=max(1,s(2)))
    canvas.create_line(cx - wrist_w//2 + s(5), wrist_y + s(10),
                       cx + wrist_w//2 - s(5), wrist_y + s(10),
                       fill=clr, width=1, dash=(5,4))
    canvas.create_text(cx, wrist_y + s(40),
                       text=("LEFT HAND" if side=="L" else "RIGHT HAND"),
                       font=("Courier New", _fs(S,11), "bold"), fill=clr)

    th_cx = cx + tsign * (pw//2 - s(6))
    th_cy = py + s(8)

    knuck_xs = [cx + int((-pw//2 + pw//8 + pw//4 * i) * 0.86) for i in range(4)]
    for kx in knuck_xs:
        canvas.create_oval(kx-s(8), knuck_y-s(8), kx+s(8), knuck_y+s(4),
                           fill="#0e1e34", outline=clr, width=max(1,s(2)))
        canvas.create_oval(kx-s(4), knuck_y-s(5), kx+s(4), knuck_y+s(1),
                           fill="#162840", outline="")

    if side == "L":
        fingers = [
            ("Pinky",  -pw//2+s(6),    -26,   [s(28), s(20), s(13)],     "1","Q"),
            ("Ring",   -pw//6-s(2),    -11,   [s(36), s(27), s(18)],     "2","W"),
            ("Middle",  s(2),            2,   [s(40), s(30), s(20)],     "3","E"),
            ("Index",   pw//4+s(4),     15,   [s(36), s(27), s(18)],     "4","R"),
        ]
        t_kin,  t_kout  = "5","T"
        tn_kin, tn_kout = "6","G"
    else:
        fingers = [
            ("Index",  -pw//4-s(4),   -15,   [s(36), s(27), s(18)],     "9","U"),
            ("Middle", -s(2),           -2,   [s(40), s(30), s(20)],     "0","I"),
            ("Ring",    pw//6+s(2),     11,   [s(36), s(27), s(18)],     "[","O"),
            ("Pinky",   pw//2-s(6),     26,   [s(28), s(20), s(13)],     "]","P"),
        ]
        t_kin,  t_kout  = "8","Y"
        tn_kin, tn_kout = "7","H"

    def draw_finger(name, bx_off, angle_deg, lengths, k_in, k_out):
        rad   = math.radians(angle_deg)
        sin_r = math.sin(rad)
        cos_r = math.cos(rad)

        pts = [(cx + bx_off, knuck_y)]
        for length in lengths:
            px2, py2 = pts[-1]
            pts.append((px2 + length * sin_r, py2 - length * cos_r))

        for i2, ((x1,y1),(x2,y2)) in enumerate(zip(pts, pts[1:])):
            tw = [s(8), s(6), s(5)][min(i2, 2)]
            canvas.create_line(x1,y1,x2,y2, fill=clr, width=tw*2, capstyle="round")
            canvas.create_line(x1,y1,x2,y2, fill="#0c1828", width=tw, capstyle="round")

        canvas.create_oval(pts[0][0]-s(7), pts[0][1]-s(7),
                           pts[0][0]+s(7), pts[0][1]+s(7),
                           fill=clr, outline=BG, width=1)
        canvas.create_oval(pts[0][0]-s(3), pts[0][1]-s(3),
                           pts[0][0]+s(3), pts[0][1]+s(3), fill=BG, outline="")
        for jx2, jy2 in pts[1:-1]:
            canvas.create_oval(jx2-s(5),jy2-s(5),jx2+s(5),jy2+s(5),
                               fill=clr, outline=BG, width=1)
            canvas.create_oval(jx2-s(2),jy2-s(2),jx2+s(2),jy2+s(2), fill=BG, outline="")

        tx, ty = pts[-1]
        canvas.create_oval(int(tx-s(6)), int(ty-s(3)),
                           int(tx+s(6)), int(ty+s(7)),
                           fill="#162840", outline=clr, width=1)

        lx2 = int(tx + sin_r * lbl_gap)
        ly2 = int(ty - cos_r * lbl_gap)
        canvas.create_text(lx2, ly2, text=name,
                           font=("Courier New", fs_l, "bold"), fill=clr, anchor="center")
        _stack(lx2, ly2, k_in, k_out)

    for args in fingers:
        draw_finger(*args)

    t_angle = tsign * 68
    tr      = math.radians(t_angle)
    tb_x    = cx + tsign * (pw//2 - s(12))
    tb_y    = py - s(16)
    t_lens  = [s(32), s(24)]

    t_pts = [(tb_x, tb_y)]
    for ln in t_lens:
        lx3, ly3 = t_pts[-1]
        t_pts.append((int(lx3 + ln * math.sin(tr)),
                      int(ly3 - ln * abs(math.cos(tr)))))

    for i3, ((x1,y1),(x2,y2)) in enumerate(zip(t_pts, t_pts[1:])):
        tw = [s(10), s(7)][i3]
        canvas.create_line(x1,y1,x2,y2, fill=clr, width=tw*2, capstyle="round")
        canvas.create_line(x1,y1,x2,y2, fill="#0c1828", width=tw, capstyle="round")
    for jx3, jy3 in t_pts:
        canvas.create_oval(jx3-s(5),jy3-s(5),jx3+s(5),jy3+s(5),
                           fill=clr, outline=BG, width=1)
    tt_x, tt_y = t_pts[-1]
    canvas.create_oval(tt_x-s(7), tt_y-s(3), tt_x+s(7), tt_y+s(7),
                       fill="#162840", outline=clr, width=1)

    t_sin = math.sin(tr)
    t_cos = abs(math.cos(tr))
    tl_x  = int(tt_x + t_sin * lbl_gap)
    tl_y  = int(tt_y - t_cos * lbl_gap)
    canvas.create_text(tl_x, tl_y-s(5), text="Thumb",
                       font=("Courier New", fs_l, "bold"), fill=clr, anchor="center")
    _stack(tl_x, tl_y, t_kin, t_kout)

    tn_x = th_cx + tsign * s(44)
    tn_y = th_cy
    canvas.create_text(tn_x, tn_y-s(18), text="Thenar",
                       font=("Courier New", fs_l, "bold"), fill=clr, anchor="center")
    _stack(tn_x, tn_y+s(50), tn_kin, tn_kout)

    canvas.create_text(w//2, s(14),
                       text="−  contract    +  extend",
                       font=("Courier New", _fs(S,9)), fill=TEXT_DIM)


#  ARM MODE
def draw_arm(canvas, w, h, side, pressed):
    canvas.delete("all")
    _grid(canvas, w, h)

    clr  = LEFT_CLR if side == "L" else RIGHT_CLR
    S    = min(w / 380.0, h / 760.0)
    def s(v): return max(1, int(v * S))

    bw    = s(21);  bh = s(11)
    bstep = bh * 2 + s(5)
    fs_s  = _fs(S, 11);  fs_k = _fs(S, 9);  fs_l = _fs(S, 10)

    def _seg(x1, y1, x2, y2, thick):
        canvas.create_line(x1, y1, x2, y2,
                           fill=clr, width=max(4, thick),
                           capstyle="round", joinstyle="round")

    def _jnt(jx, jy, r):
        canvas.create_oval(jx-r, jy-r, jx+r, jy+r,
                           fill="#0a1820", outline=clr, width=max(3, s(4)))
        canvas.create_oval(jx-r//3, jy-r//3, jx+r//3, jy+r//3,
                           fill=clr, outline="")

    def _lbl(lx, ly, name, k_in, k_out):
        canvas.create_text(lx, ly, text=name,
                           font=("Courier New", fs_l, "bold"),
                           fill=clr, anchor="center")
        in_a  = k_in.lower()  in pressed
        out_a = k_out.lower() in pressed
        _badge(canvas, lx, ly - bstep,   bw, bh, "+", k_out, out_a, clr, fs_s, fs_k)
        _badge(canvas, lx, ly - bstep*2, bw, bh, "-", k_in,  in_a,  clr, fs_s, fs_k)

    def _tick(x1, y1, x2, y2):
        canvas.create_line(x1, y1, x2, y2,
                           fill=clr, width=max(1, s(2)), dash=(4, 3))

    if side == "L":
        cx_stub = int(w * 0.62)
        sh_x    = int(w * 0.22)
    else:
        cx_stub = int(w * 0.38)
        sh_x    = int(w * 0.78)

    stub_hw  = s(24)
    stub_top = int(h * 0.18)
    stub_bot = int(h * 0.42)
    stub_r   = stub_hw
    arm_y    = stub_top + stub_r

    sh_y  = arm_y
    row_min  = bstep * 2 + bh + s(6)
    row_max  = int(h * 0.92) - bh
    n        = 6
    spacing  = (row_max - row_min) // (n - 1)
    spacing  = max(spacing, bstep * 2 + s(20))

    # Core
    wall = max(6, s(14))
    canvas.create_line(cx_stub - stub_hw, stub_bot+stub_r-s(20),
                       cx_stub - stub_hw, stub_bot-s(80),
                       fill=clr, width=wall)
    canvas.create_line(cx_stub + stub_hw, stub_bot+stub_r-s(20),
                       cx_stub + stub_hw, stub_bot-s(80),
                       fill=clr, width=wall)
    canvas.create_rectangle(cx_stub - stub_hw + wall//2, stub_bot+stub_r-s(20),
                             cx_stub + stub_hw - wall//2, stub_bot-s(80),
                             fill="#0c1a2e", outline="")
    canvas.create_arc(cx_stub - stub_hw, stub_top+s(80),
                      cx_stub + stub_hw, stub_top + stub_r * 2+s(80),
                      start=0, extent=180,
                      outline=clr, style="arc", width=wall)

    if side == "L":
        core_kin, core_kout = "6","G"
    else:
        core_kin, core_kout = "7","H"
    _jnt(cx_stub, stub_bot+stub_r-s(20), s(11))
    _tick(cx_stub, stub_bot+stub_r-s(20), cx_stub, stub_bot+s(50))
    _lbl(cx_stub, stub_bot+s(100), "Core", core_kin, core_kout)

    # Arm
    if side == "L":
        arm_kin, arm_kout = "5","T"
        arm_start = cx_stub - stub_hw if side == "L" else cx_stub + stub_hw
        sw_arm = max(8, s(20))
        _seg(arm_start, arm_y+s(70), sh_x+s(70), sh_y+s(70), sw_arm)
        arm_mid_x = (arm_start + sh_x) // 2
        _tick(arm_mid_x+s(40), arm_y - sw_arm//2+s(50), arm_mid_x+s(40), sh_y+s(70))
        _lbl(arm_mid_x+s(40), arm_y - sw_arm//2+s(40), "Arm", arm_kin, arm_kout)
    else:
        arm_kin, arm_kout = "8","Y"
        arm_start = cx_stub - stub_hw if side == "L" else cx_stub + stub_hw
        sw_arm = max(8, s(20))
        _seg(arm_start, arm_y+s(70), sh_x-s(70), sh_y+s(70), sw_arm)
        arm_mid_x = (arm_start + sh_x) // 2
        _tick(arm_mid_x-s(40), arm_y - sw_arm//2+s(50), arm_mid_x-s(40), sh_y+s(70))
        _lbl(arm_mid_x-s(40), arm_y - sw_arm//2+s(40), "Arm", arm_kin, arm_kout)

    # Shoulder
    if side == "L":
        sh_kin, sh_kout = "4","R"
        _jnt(sh_x+s(70), sh_y+s(70), s(16))
        _tick(sh_x+s(70), sh_y+s(70), sh_x, sh_y+s(70))
        _lbl(sh_x, sh_y+s(95), "Shoulder", sh_kin, sh_kout)
    else:
        sh_kin, sh_kout = "9","U"
        _jnt(sh_x-s(70), sh_y+s(70), s(16))
        _tick(sh_x-s(70), sh_y+s(70), sh_x, sh_y+s(70))
        _lbl(sh_x, sh_y+s(95), "Shoulder", sh_kin, sh_kout)

    # UpperArm
    sw_ua = max(7, s(20))
    if side == "L":
        ua_kin, ua_kout = "3","E"
        _seg(sh_x+s(70), sh_y+s(70), sh_x+s(50), sh_y+s(200), sw_ua)
        ua_mx = (sh_x+s(70) + sh_x+s(50)) // 2
        ua_my = (sh_y+s(70) + sh_y+s(200)) // 2
        _tick(ua_mx, ua_my, sh_x, ua_my)
        _lbl(sh_x-s(10), sh_y+s(185), "UpperArm", ua_kin, ua_kout)
    else:
        ua_kin, ua_kout = "0","I"
        _seg(sh_x-s(70), sh_y+s(70), sh_x-s(50), sh_y+s(200), sw_ua)
        ua_mx = (sh_x-s(70) + sh_x-s(50)) // 2
        ua_my = (sh_y+s(70) + sh_y+s(200)) // 2
        _tick(ua_mx, ua_my, sh_x, ua_my)
        _lbl(sh_x+s(10), sh_y+s(185), "UpperArm", ua_kin, ua_kout)

    # ELbow
    if side == "L":
        el_kin, el_kout = "2","W"
        _jnt(sh_x+s(50), sh_y+s(200), s(16))
        _tick(sh_x+s(50), sh_y+s(200), sh_x, sh_y+s(230))
        _lbl(sh_x-s(10), sh_y+s(290), "Elbow", el_kin, el_kout)
    else:
        el_kin, el_kout = "[","O"
        _jnt(sh_x-s(50), sh_y+s(200), s(16))
        _tick(sh_x-s(50), sh_y+s(200), sh_x, sh_y+s(230))
        _lbl(sh_x+s(10), sh_y+s(290), "Elbow", el_kin, el_kout)

    # Wrist
    sw_wr = max(6, s(20))
    if side == "L":
        wr_kin, wr_kout = "1","Q"
        _seg(sh_x+s(50), sh_y+s(200), sh_x+s(70), sh_y+s(300), sw_wr)
        _jnt(sh_x+s(70), sh_y+s(300), s(16))
        _tick(sh_x+s(60), sh_y+s(250), sh_x+s(10), sh_y+s(330))
        _lbl(sh_x+s(10), sh_y+s(380), "Wrist", wr_kin, wr_kout)
    else:
        wr_kin, wr_kout = "]","P"
        _seg(sh_x-s(50), sh_y+s(200), sh_x-s(70), sh_y+s(300), sw_wr)
        _jnt(sh_x-s(70), sh_y+s(300), s(16))
        _tick(sh_x-s(60), sh_y+s(250), sh_x-s(10), sh_y+s(330))
        _lbl(sh_x-s(10), sh_y+s(380), "Wrist", wr_kin, wr_kout)
    

    canvas.create_text(w // 2, s(14),
                       text=("LEFT ARM" if side == "L" else "RIGHT ARM"),
                       font=("Courier New", _fs(S, 11), "bold"), fill=clr)
    canvas.create_text(w // 2, h - s(12),
                       text="-  contract (IN)    +  extend (OUT)",
                       font=("Courier New", _fs(S, 9)), fill=TEXT_DIM)


class CameraThread:
    def __init__(self, on_frame):
        self.on_frame = on_frame
        self.running = False
        self._thread = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _loop(self):
        if not CV2_AVAILABLE:
            return

        stream = urllib.request.urlopen("http://10.228.183.64/video")
        bytes_data = b''

        while self.running:
            bytes_data += stream.read(4096)

            a = bytes_data.find(b'\xff\xd8')
            b = bytes_data.find(b'\xff\xd9')

            if a != -1 and b != -1:
                jpg = bytes_data[a:b+2]
                bytes_data = bytes_data[b+2:]

                frame = cv2.imdecode(
                    np.frombuffer(jpg, dtype=np.uint8),
                    cv2.IMREAD_COLOR
                )

                if frame is not None:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.on_frame(frame_rgb)
# ═════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ═════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    KEYSYM_MAP = {"bracketleft": "[", "bracketright": "]"}

    def __init__(self):
        super().__init__()
        self.ctrl = RDKController()
        self.title("RDK ROBOT CONTROLLER")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(960, 620)
        self.geometry("1440x880")
        try:    self.state("zoomed")
        except:
            try: self.attributes("-zoomed", True)
            except: pass

        self.fn_title   = tkfont.Font(family="Courier New", size=18, weight="bold")
        self.fn_section = tkfont.Font(family="Courier New", size=12, weight="bold")
        self.fn_mono    = tkfont.Font(family="Courier New", size=11, weight="bold")
        self.fn_label   = tkfont.Font(family="Courier New", size=10)
        self.fn_small   = tkfont.Font(family="Courier New", size=9)

        self.status_var   = tk.StringVar(value="DISCONNECTED")
        self.log_var      = tk.StringVar(value="—")
        self._pressed     = set()
        self._speed_level = 2
        self.key_widgets  = {}
        self._key_timers  = {}

        self._cam_photo = None
        self._cam_thread = CameraThread(self._on_cam_frame)
        if CV2_AVAILABLE:
            self._cam_thread.start()

        self._build_ui()
        self._bind_keys()
        self._render_mode("B")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(150, self._toggle_connect)
        self.bind("<Configure>", lambda e: self.after(80, self._redraw_all))

    def _on_cam_frame(self, frame_rgb):
        """Called from camera thread — schedule canvas update on main thread."""
        self.after(0, lambda f=frame_rgb: self._update_cam_canvas(f))

    def _update_cam_canvas(self, frame_rgb):
        cw = self.cam_canvas.winfo_width()
        ch = self.cam_canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        img  = Image.fromarray(frame_rgb)
        img  = img.resize((cw, ch), Image.BILINEAR)
        self._cam_photo = ImageTk.PhotoImage(img)   # keep reference!
        self.cam_canvas.delete("all")
        self.cam_canvas.create_image(0, 0, anchor="nw", image=self._cam_photo)

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG, pady=10)
        hdr.pack(fill="x", padx=22)
        tk.Label(hdr, text="RDK ", font=self.fn_title,
                 bg=BG, fg=ACCENT_B).pack(side="left")
        tk.Label(hdr, text="ROBOT CONTROLLER", font=self.fn_title,
                 bg=BG, fg=TEXT_BRIGHT).pack(side="left")
        self.conn_dot = tk.Label(hdr, text="⬤", font=self.fn_mono, bg=BG, fg=DANGER)
        self.conn_dot.pack(side="right", padx=(4,0))
        tk.Label(hdr, textvariable=self.status_var, font=self.fn_label,
                 bg=BG, fg=TEXT_MID).pack(side="right", padx=(0,6))
        self.btn_connect = tk.Button(
            hdr, text="CONNECT", font=self.fn_section, bg=BORDER, fg=ACCENT_B,
            relief="flat", bd=0, padx=12, pady=5, cursor="hand2",
            activebackground=KEY_BG, command=self._toggle_connect)
        self.btn_connect.pack(side="right", padx=(6,12))

        tk.Label(hdr, text="PORT:", font=self.fn_small,
                 bg=BG, fg=TEXT_DIM).pack(side="right", padx=(8,2))
        self.port_var = tk.StringVar(value=str(PORT))
        pe = tk.Entry(hdr, textvariable=self.port_var, font=self.fn_mono,
                      bg=KEY_BG, fg=ACCENT_B, insertbackground=ACCENT_B,
                      relief="flat", highlightbackground=BORDER,
                      highlightthickness=1, width=6)
        pe.pack(side="right")
        pe.bind("<FocusIn>",  lambda e: self.unbind("<KeyPress>"))
        pe.bind("<FocusOut>", lambda e: self._bind_keys())

        tk.Label(hdr, text="IP:", font=self.fn_small,
                 bg=BG, fg=TEXT_DIM).pack(side="right", padx=(14,2))
        self.ip_var = tk.StringVar(value=RDK_IP)
        ie = tk.Entry(hdr, textvariable=self.ip_var, font=self.fn_mono,
                      bg=KEY_BG, fg=ACCENT_B, insertbackground=ACCENT_B,
                      relief="flat", highlightbackground=BORDER,
                      highlightthickness=1, width=16)
        ie.pack(side="right")
        ie.bind("<FocusIn>",  lambda e: self.unbind("<KeyPress>"))
        ie.bind("<FocusOut>", lambda e: self._bind_keys())

        tk.Frame(self, bg=BORDER, height=2).pack(fill="x", padx=22)

        tab_row = tk.Frame(self, bg=BG, pady=8)
        tab_row.pack(fill="x", padx=22)
        tk.Label(tab_row, text="MODE:", font=self.fn_section,
                 bg=BG, fg=TEXT_DIM).pack(side="left", padx=(0,12))
        self.tab_btns = {}
        for m, lbl in [("B","  B · BODY  "),("N","  N · HANDS  "),("V","  V · ARMS  ")]:
            btn = tk.Button(tab_row, text=lbl, font=self.fn_section,
                            bg=PANEL, fg=TEXT_DIM, relief="flat", bd=0,
                            padx=10, pady=7, cursor="hand2",
                            activebackground=KEY_BG,
                            command=lambda mm=m: self._select_mode(mm))
            btn.pack(side="left", padx=3)
            self.tab_btns[m] = btn

        tk.Frame(self, bg=BORDER, height=2).pack(fill="x", padx=22)

        self.content = tk.Frame(self, bg=BG)
        self.content.pack(fill="both", expand=True, padx=10, pady=8)
        self.content.columnconfigure(0, weight=10)
        self.content.columnconfigure(1, weight=80)
        self.content.columnconfigure(2, weight=10)
        self.content.rowconfigure(0, weight=1)

        lw = tk.Frame(self.content, bg=BORDER)
        lw.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        lw.rowconfigure(0, weight=1);  lw.columnconfigure(0, weight=1)
        self.left_canvas = tk.Canvas(lw, bg=BG, highlightthickness=0)
        self.left_canvas.grid(sticky="nsew", padx=1, pady=1)

        cam_wrap = tk.Frame(self.content, bg=CAM_BORDER)
        cam_wrap.grid(row=0, column=1, sticky="nsew", padx=4)
        cam_wrap.rowconfigure(1, weight=1);  cam_wrap.columnconfigure(0, weight=1)
        cam_hdr = tk.Frame(cam_wrap, bg="#080f18", pady=5)
        cam_hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(cam_hdr, text="▶  CAMERA FEED", font=self.fn_small,
                 bg="#080f18", fg=TEXT_DIM).pack(side="left", padx=10)
        tk.Label(cam_hdr, text="● REC", font=self.fn_small,
                 bg="#080f18", fg=DANGER).pack(side="right", padx=10)
        self.cam_canvas = tk.Canvas(cam_wrap, bg=CAM_BG, highlightthickness=0)
        self.cam_canvas.grid(row=1, column=0, sticky="nsew", padx=2, pady=(0,2))
        self.cam_canvas.bind("<Configure>",
                             lambda e: self.after(30, self._draw_cam_placeholder))

        rw = tk.Frame(self.content, bg=BORDER)
        rw.grid(row=0, column=2, sticky="nsew", padx=(5,0))
        rw.rowconfigure(0, weight=1);  rw.columnconfigure(0, weight=1)
        self.right_canvas = tk.Canvas(rw, bg=BG, highlightthickness=0)
        self.right_canvas.grid(sticky="nsew", padx=1, pady=1)

        tk.Frame(self, bg=BORDER, height=2).pack(fill="x", padx=22, pady=(4,0))
        log_row = tk.Frame(self, bg=BG, pady=6)
        log_row.pack(fill="x", padx=22)
        tk.Label(log_row, text="CMD:", font=self.fn_section,
                 bg=BG, fg=TEXT_DIM).pack(side="left", padx=(0,8))
        tk.Label(log_row, textvariable=self.log_var,
                 font=self.fn_mono, bg=BG, fg=ACCENT_B).pack(side="left")
        tk.Label(log_row, text="ESC · exit   B · BODY   N · HANDS   V · ARMS",
                 font=self.fn_small, bg=BG, fg=TEXT_DIM).pack(side="right")

    def _draw_cam_placeholder(self):
        self.cam_canvas.delete("all")
        cw = self.cam_canvas.winfo_width()
        ch = self.cam_canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        cx, cy = cw//2, ch//2
        for y in range(0, ch, 4):
            self.cam_canvas.create_line(0, y, cw, y, fill="#0c1016", width=1)
        bc, bl = "#162840", 28
        for ox, oy, sx, sy in [(0,0,1,1),(cw,0,-1,1),(0,ch,1,-1),(cw,ch,-1,-1)]:
            self.cam_canvas.create_line(ox, oy, ox+sx*bl, oy, fill=bc, width=2)
            self.cam_canvas.create_line(ox, oy, ox, oy+sy*bl, fill=bc, width=2)
        self.cam_canvas.create_line(cx-14,cy, cx+14,cy, fill="#162840", width=1)
        self.cam_canvas.create_line(cx,cy-14, cx,cy+14, fill="#162840", width=1)
        self.cam_canvas.create_oval(cx-6,cy-6, cx+6,cy+6, fill="", outline="#162840")
        self.cam_canvas.create_text(cx, cy+28, text="NO SIGNAL",
                                    font=("Courier New",11,"bold"), fill="#182a40")
        self.cam_canvas.create_text(cx, cy+48, text="connect camera feed here",
                                    font=("Courier New",9), fill="#0f1e2e")

    def _render_mode(self, mode):
        self.ctrl.mode = mode
        self._update_tabs(mode)
        self.after(80, self._redraw_all)

    def _redraw_all(self):
        mode = self.ctrl.mode
        for c in (self.left_canvas, self.right_canvas):
            c.update_idletasks()
        lw = self.left_canvas.winfo_width()
        lh = self.left_canvas.winfo_height()
        rw2= self.right_canvas.winfo_width()
        rh = self.right_canvas.winfo_height()
        if lw < 10 or lh < 10:
            return
        acc = MODE_ACCENTS[mode]
        if mode == "B":
            draw_body_left(self.left_canvas,  lw, lh, acc, self._pressed)
            draw_body_right(self.right_canvas, rw2, rh, acc, self._pressed,
                            self._speed_level)
        elif mode == "N":
            draw_hand(self.left_canvas,  lw, lh, "L", self._pressed)
            draw_hand(self.right_canvas, rw2, rh, "R", self._pressed)
        elif mode == "V":
            draw_arm(self.left_canvas,  lw, lh, "L", self._pressed)
            draw_arm(self.right_canvas, rw2, rh, "R", self._pressed)

    def _update_tabs(self, active):
        for m, btn in self.tab_btns.items():
            acc = MODE_ACCENTS[m]
            btn.config(bg=BORDER if m==active else PANEL,
                       fg=acc    if m==active else TEXT_DIM)

    def _bind_keys(self):
        self.bind("<KeyPress>",   self._on_press)
        self.bind("<KeyRelease>", self._on_release)
        self.focus_set()

    def _norm(self, e):
        if e.char and e.char.isprintable():
            return e.char.lower()
        return self.KEYSYM_MAP.get(e.keysym.lower(), e.keysym.lower())

    # ── Key highlight ─────────────────────────────────────────────────────
    def _flash_key(self, key_char):
        """Light up a key badge and keep it lit while the key is held."""
        kc = key_char.lower()
        # Cancel any pending unflash timer so the badge stays lit
        if kc in self._key_timers:
            self.after_cancel(self._key_timers.pop(kc))
        self._redraw_all()   # canvas-based panels reflect _pressed set immediately

    def _unflash_key(self, key_char):
        """Dim the key badge after release."""
        kc = key_char.lower()
        self._key_timers.pop(kc, None)
        self._redraw_all()

    # ── Press / Release ───────────────────────────────────────────────────
    def _on_press(self, e):
        key = self._norm(e)
        if e.keysym.lower() == "escape":
            self._on_close(); return
        if key == "b": self._select_mode("B"); return
        if key == "n": self._select_mode("N"); return
        if key == "v": self._select_mode("V"); return

        # Drop OS key-repeat events — repetition is handled by the send loop
        if key in self._pressed:
            return

        self._pressed.add(key)
        mode = self.ctrl.mode

        if mode == "B":
            body_map = {
                "w": "w", "s": "s", "a": "a", "d": "d",
                "i": "i", "k": "k", "j": "j", "l": "l",
            }
            speed_map = {"0": 0, "1": 1, "2": 2, "3": 3}

            if key in body_map:
                cmd = body_map[key]
                ok  = self.ctrl.send(cmd)          # immediate + repeating
                self.log_var.set(f"TX → {cmd.upper()}" if ok
                                 else f"TX FAILED → {cmd.upper()}  (disconnected?)")
                if ok:
                    self._flash_key(key)
                else:
                    self._set_status(False, "Send failed — connection lost")

            elif key in speed_map:
                self._speed_level = speed_map[key]
                cmd = f"S{key}"
                ok  = self.ctrl.send_immediate(cmd) # one-shot only
                self.log_var.set(f"TX → {cmd}" if ok
                                 else f"TX FAILED → {cmd}  (disconnected?)")
                if ok:
                    self._flash_key(key)
                else:
                    self._set_status(False, "Send failed — connection lost")

        elif mode in ("N", "V"):
            finger_keys = {
                '1','2','3','4','5','6','7','8','9','0','[',']',
                'q','w','e','r','t','g','h','y','u','i','o','p',
                'a','s','d','f'
            }
            if key in finger_keys:
                ok = self.ctrl.send(key)            # immediate + repeating
                self.log_var.set(f"TX → {key.upper()}" if ok
                                 else f"TX FAILED → {key.upper()}  (disconnected?)")
                if ok:
                    self._flash_key(key)
                else:
                    self._set_status(False, "Send failed — connection lost")

        self._redraw_all()

    def _on_release(self, e):
        key = self._norm(e)
        self._pressed.discard(key)

        # Stop repeating — but keep going if another move key is still held
        mode = self.ctrl.mode
        if mode == "B":
            held_move = self._pressed & {"w","s","a","d","i","k","j","l"}
        elif mode in ("N", "V"):
            held_move = self._pressed & {
                '1','2','3','4','5','6','7','8','9','0','[',']',
                'q','w','e','r','t','g','h','y','u','i','o','p','a','s','d','f'
            }
        else:
            held_move = set()

        if held_move:
            last_held = next(iter(held_move))
            self.ctrl.send(last_held)
        else:
            self.ctrl.clear_pending()

        # Schedule unflash with a short tail (150 ms) so release feels snappy
        kc = key.lower()
        if kc in self._key_timers:
            self.after_cancel(self._key_timers[kc])
        self._key_timers[kc] = self.after(150, lambda k=kc: self._unflash_key(k))

        self._redraw_all()

    def _select_mode(self, m):
        self.ctrl.send_immediate(f"MODE_{m}")
        self.log_var.set(f"MODE_{m}  ({MODE_NAMES[m]})")
        self._render_mode(m)
        self.focus_set()

    def _toggle_connect(self):
        if self.ctrl.connected:
            self.ctrl.disconnect()
            self._set_status(False)
        else:
            ip = self.ip_var.get().strip()
            try:   port = int(self.port_var.get().strip())
            except: self.log_var.set("ERROR: invalid port"); return
            if not ip: self.log_var.set("ERROR: IP empty"); return
            self.btn_connect.config(text="CONNECTING…", state="disabled")
            self.update()
            threading.Thread(target=self._do_connect,
                             args=(ip,port), daemon=True).start()

    def _do_connect(self, ip, port):
        ok, err = self.ctrl.connect(ip, port)
        self.after(0, lambda: self._set_status(ok, err))

    def _set_status(self, connected, err=None):
        if connected:
            ip   = self.ip_var.get().strip()
            port = self.port_var.get().strip()
            self.status_var.set("CONNECTED")
            self.conn_dot.config(fg=ACCENT_N)
            self.btn_connect.config(text="DISCONNECT", state="normal", fg=DANGER)
            self.log_var.set(f"Connected  {ip}:{port}")
        else:
            msg = err.split("]")[-1].strip() if err else "Connection failed"
            self.status_var.set("DISCONNECTED")
            self.conn_dot.config(fg=DANGER)
            self.btn_connect.config(text="CONNECT", state="normal", fg=ACCENT_B)
            self.log_var.set(f"ERROR: {msg}")

    def _on_close(self):
        self.ctrl.disconnect()
        self._cam_thread.stop()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
