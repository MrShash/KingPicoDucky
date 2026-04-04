import wifi
import time
import random
import usb_hid
import socketpool
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
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

def wait_ms(ms):
    t = float(ms) / 1000.0
    while t > 0:
        if feed_abort:
            return
        s = min(0.05, t)
        time.sleep(s)
        t -= s

feed_abort = False
busy = False
humanize_type = False

def type_jitter(s):
    n = len(s)
    for i in range(n):
        if feed_abort:
            return
        layout.write(s[i])
        if i + 1 < n:
            wait_ms(random.uniform(5, 35))

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
                    genHID([x])
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
                    genHID([x])
        elif ln == "EXIT":
            break
        else:
            if ln.startswith("WAIT"):
                wait_ms(float(ln.split(" ")[1]))
            elif ln.startswith("TYPE"):
                if feed_abort:
                    return
                t = ln.split(" ", 1)[1]
                if humanize_type:
                    type_jitter(t)
                else:
                    layout.write(t)
            else:
                press(cvt(ln))
        i += 1

def runHID(script, hz=False):
    global busy, feed_abort, humanize_type
    if busy:
        return "busy"
    busy = True
    feed_abort = False
    humanize_type = hz
    try:
        genHID(script)
    finally:
        busy = False
        humanize_type = False
    st = "aborted" if feed_abort else "done"
    print(st)
    return st

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

@server.route("/execute", POST, append_slash=True)
def r_exe(request):
    try:
        j = request.json() or {}
        raw = j.get("content", "")
        hz = j.get("humanize", False)
        if isinstance(hz, str):
            hz = hz.lower() in ("1", "true", "yes")
        elif not isinstance(hz, bool):
            hz = bool(hz)
        if not isinstance(raw, str):
            return JSONResponse(request, {"message": "bad format"}, status_code=400)
        st = runHID(raw.splitlines(), hz)
        if st == "busy":
            return JSONResponse(request, {"message": "busy"}, status_code=429)
        return JSONResponse(request, {"message": st})
    except Exception as e:
        print(e)
        return JSONResponse(request, {"message": "error"}, status_code=500)

try:
    print("http://", nc["ip"], sep="")
    server.serve_forever(nc["ip"], 80)
except KeyboardInterrupt:
    print("bye")
