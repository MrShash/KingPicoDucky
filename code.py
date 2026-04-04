import wifi
import time
import random
import usb_hid
import socketpool
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.mouse import Mouse
from adafruit_httpserver import Server, Request, JSONResponse, GET, POST, FileResponse

def read_cfg(fn="network.conf"):
    cfg = {}
    try:
        with open(fn, "r") as f:
            for ln in f:
                ln = ln.strip()
                if ln and "=" in ln:
                    k, v = ln.split("=", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    except Exception as e:
        print("cfg:", e)
    return cfg

nc = read_cfg()
wifi.radio.stop_station()
wifi.radio.start_ap(nc["ssid"], nc["password"])

pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, "/static", debug=True)
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)
try:
    mouse = Mouse(usb_hid.devices)
except Exception as e:
    print("Mouse disabled or unavailable:", e)
    mouse = None

hidKeys = {
    'A': Keycode.A, 'B': Keycode.B, 'C': Keycode.C, 'D': Keycode.D, 'E': Keycode.E,
    'F': Keycode.F, 'G': Keycode.G, 'H': Keycode.H, 'I': Keycode.I, 'J': Keycode.J,
    'K': Keycode.K, 'L': Keycode.L, 'M': Keycode.M, 'N': Keycode.N, 'O': Keycode.O,
    'P': Keycode.P, 'Q': Keycode.Q, 'R': Keycode.R, 'S': Keycode.S, 'T': Keycode.T,
    'U': Keycode.U, 'V': Keycode.V, 'W': Keycode.W, 'X': Keycode.X, 'Y': Keycode.Y,
    'Z': Keycode.Z, 'F1': Keycode.F1, 'F2': Keycode.F2, 'F3': Keycode.F3, 'F4': Keycode.F4,
    'F5': Keycode.F5, 'F6': Keycode.F6, 'F7': Keycode.F7, 'F8': Keycode.F8, 'F9': Keycode.F9,
    'F10': Keycode.F10, 'F11': Keycode.F11, 'F12': Keycode.F12, 'LEFT': Keycode.LEFT_ARROW,
    'UP': Keycode.UP_ARROW, 'RIGHT': Keycode.RIGHT_ARROW, 'DOWN': Keycode.DOWN_ARROW,
    'TAB': Keycode.TAB, 'HOME': Keycode.HOME, 'END': Keycode.END, 'PGUP': Keycode.PAGE_UP,
    'PGDN': Keycode.PAGE_DOWN, 'CAPS': Keycode.CAPS_LOCK, 'NUM': Keycode.KEYPAD_NUMLOCK,
    'SCROLL': Keycode.SCROLL_LOCK, 'CTRL': Keycode.CONTROL, 'SHIFT': Keycode.SHIFT, 'ALT': Keycode.ALT,
    'GUI': Keycode.GUI, 'ESC': Keycode.ESCAPE, 'PRTSCR': Keycode.PRINT_SCREEN, 'PAUSE': Keycode.PAUSE,
    'SPACE': Keycode.SPACE, 'DEL': Keycode.DELETE, 'INSERT': Keycode.INSERT, 'BKSP': Keycode.BACKSPACE,
    'ENTER': Keycode.ENTER, 'APP': Keycode.APPLICATION
}

def cvt(ln):
    out = []
    for k in filter(None, ln.split(" ")):
        k = k.upper()
        c = hidKeys.get(k)
        if c is not None:
            out.append(c)
        elif hasattr(Keycode, k):
            out.append(getattr(Keycode, k))
        else:
            print("unknown key", k)
    return out

def press(seq):
    for kd in seq:
        kbd.press(kd)
    kbd.release_all()



feed_abort = False
busy = False
humanize_type = False
humanize_freq = 0.15
humanize_px = 2
humanize_px = 2
mouse_offset_x = 0
mouse_offset_y = 0
current_generator = None
wait_until = 0

jig_enabled = False
jig_dist = 10
jig_interval = 10.0
jig_rand = True
last_jig_time = 0

def get_natural_delay(char):
    base = random.uniform(20, 60) / 1000.0
    if char in ' \t':
        return random.uniform(40, 100) / 1000.0
    elif char in '.,;:!?\n':
        return random.uniform(150, 400) / 1000.0
    else:
        if random.random() < 0.05:  # 5% chance of a longer pause
            return random.uniform(100, 200) / 1000.0
        return base

def jiggle_mouse():
    global mouse_offset_x, mouse_offset_y
    if mouse is None:
        return
        
    if mouse_offset_x != 0 or mouse_offset_y != 0:
        try:
            mouse.move(x=-mouse_offset_x, y=-mouse_offset_y)
            mouse_offset_x = 0
            mouse_offset_y = 0
        except Exception:
            pass
        return
        
    if random.random() < humanize_freq:
        dx = random.randint(2, humanize_px) if humanize_px >= 2 else 2
        dy = random.randint(2, humanize_px) if humanize_px >= 2 else 2
        if random.random() < 0.5: dx = -dx
        if random.random() < 0.5: dy = -dy
        try:
            mouse.move(x=dx, y=dy)
            mouse_offset_x = dx
            mouse_offset_y = dy
        except Exception:
            pass

def type_jitter(s):
    n = len(s)
    for i in range(n):
        if feed_abort:
            return
        layout.write(s[i])
        jiggle_mouse()
        if i + 1 < n:
            yield get_natural_delay(s[i])

def genHID(script):
    i, n = 0, len(script)
    while i < n:
        if feed_abort:
            return
        ln = script[i].strip()
        if ln.startswith("LOOP"):
            cnt = int(ln.split(" ")[1])
            i += 1
            blk = []
            while i < n and script[i].strip() != "EXIT":
                blk.append(script[i])
                i += 1
            for _ in range(cnt):
                if feed_abort:
                    return
                for x in blk:
                    for y in genHID([x]):
                        yield y
        elif ln == "INF":
            i += 1
            blk = []
            while i < n and script[i].strip() != "EXIT":
                blk.append(script[i])
                i += 1
            while not feed_abort:
                for x in blk:
                    if feed_abort:
                        return
                    for y in genHID([x]):
                        yield y
        elif ln == "EXIT":
            break
        else:
            if ln.startswith("WAIT"):
                yield float(ln.split(" ")[1]) / 1000.0
            elif ln.startswith("TYPE"):
                if feed_abort:
                    return
                t = ln.split(" ", 1)[1]
                if humanize_type:
                    for y in type_jitter(t):
                        yield y
                else:
                    layout.write(t)
                    yield 0.01
            else:
                press(cvt(ln))
                yield 0.01
        i += 1

def runHID(script, hz=False, h_freq=0.15, h_px=2):
    global busy, feed_abort, humanize_type, humanize_freq, humanize_px, current_generator, wait_until

    if busy:
        return "busy"
    busy = True
    feed_abort = False
    humanize_type = hz
    humanize_freq = float(h_freq)
    humanize_px = int(h_px)
    current_generator = genHID(script)
    wait_until = time.monotonic()
    return "started"

@server.route("/", GET)
def r_root(request):
    return FileResponse(request, filename="index.html")

@server.route("/index.html", [GET, POST])
def r_idx(request):
    return FileResponse(request, filename="index.html")

@server.route("/styles.css", [GET, POST])
def r_css(request):
    return FileResponse(request, filename="styles.css", content_type="text/css")

@server.route("/style.css", [GET, POST])
def r_css_alias(request):
    return FileResponse(request, filename="styles.css", content_type="text/css")

@server.route("/script.js", [GET, POST])
def r_js(request):
    return FileResponse(request, filename="script.js", content_type="application/javascript")

@server.route("/stop", POST, append_slash=True)
def r_stop(request):
    global feed_abort
    feed_abort = True
    return JSONResponse(request, {"ok": True, "message": "stop"})

@server.route("/status", GET, append_slash=True)
def r_stat(request):
    return JSONResponse(request, {"busy": busy, "abort": feed_abort})

@server.route("/jiggler", POST, append_slash=True)
def r_jig(request):
    global jig_enabled, jig_dist, jig_interval, jig_rand, last_jig_time
    try:
        j = request.json() or {}
        jig_enabled = bool(j.get("enabled", False))
        jig_dist = min(127, max(1, int(j.get("distance", 10))))
        jig_interval = max(0.5, float(j.get("interval", 10.0)))
        jig_rand = bool(j.get("random", True))
        last_jig_time = time.monotonic()
        return JSONResponse(request, {"ok": True})
    except Exception as e:
        return JSONResponse(request, {"ok": False}, status_code=400)

@server.route("/execute", POST, append_slash=True)
def r_exe(request):
    try:
        j = request.json() or {}
        raw = j.get("content", "")
        hz = j.get("humanize", False)
        hz_freq = float(j.get("hz_freq", 0.15))
        hz_px = int(j.get("hz_px", 2))
        if isinstance(hz, str):
            hz = hz.lower() in ("1", "true", "yes")
        elif not isinstance(hz, bool):
            hz = bool(hz)
        if not isinstance(raw, str):
            return JSONResponse(request, {"message": "bad format"}, status_code=400)
        st = runHID(raw.splitlines(), hz, hz_freq, hz_px)
        if st == "busy":
            return JSONResponse(request, {"message": "busy"}, status_code=429)
        return JSONResponse(request, {"message": st})
    except Exception as e:
        print(e)
        return JSONResponse(request, {"message": "error"}, status_code=500)

try:
    print("http://", nc["ip"], sep="")
    server.start(nc["ip"], 80)
    while True:
        try:
            server.poll()
        except Exception as e:
            print("poll err:", e)
            
        if busy and current_generator is not None:
            now = time.monotonic()
            if now >= wait_until:
                try:
                    delay = next(current_generator)
                    if delay is not None:
                        wait_until = now + delay
                except StopIteration:
                    busy = False
                    current_generator = None
                    humanize_type = False
                    print("aborted" if feed_abort else "done")
        elif busy and feed_abort:
            busy = False
            current_generator = None
            humanize_type = False
            print("aborted")
            
        if not busy and jig_enabled and mouse is not None:
            now = time.monotonic()
            if now - last_jig_time >= jig_interval:
                tgt_d = min(127, jig_dist)
                d = random.randint(1, tgt_d) if jig_rand and tgt_d > 1 else tgt_d
                dx = d * random.choice([-1, 1])
                dy = d * random.choice([-1, 1])
                try:
                    mouse.move(x=dx, y=dy)
                    mouse.move(x=-dx, y=-dy)
                except Exception:
                    pass
                last_jig_time = now
except KeyboardInterrupt:
    print("bye")
