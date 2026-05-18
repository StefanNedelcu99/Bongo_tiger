import pygame
import sys
import os
import json
import atexit
from pynput import keyboard, mouse

try:
    import win32api
    import win32con
    import win32gui
    WINDOWS_OS = True
except ImportError:
    WINDOWS_OS = False

pygame.init()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_path(filename):
    return os.path.join(BASE_DIR, filename)

# =====================================================================
# INCARCA CONFIGURAREA DIN config.json
# =====================================================================
CONFIG_FILE = get_path("config.json")

DEFAULT_CONFIG = {
    "SCALE_FACTOR": 0.2,
    "PAW_L_X_OFFSET": 0,
    "PAW_L_Y_OFFSET": 280,
    "PAW_R_X_OFFSET": 351,
    "PAW_R_Y_OFFSET": 280,
    "PAW_BOUNCE_DISTANCE": 25,
    "PAW_BOUNCE_FRAMES_KEY": 8,
    "PAW_BOUNCE_FRAMES_MOUSE_MOVE": 5,
    "PAW_BOUNCE_FRAMES_MOUSE_CLICK": 12,
    "CLICK_MESSAGE": "Rawr! \U0001f42f",
    "CLICK_MESSAGE_DURATION_FRAMES": 90,
    "SHOW_COUNTER_ON_HOVER": True,
    "COUNTER_SAVE_FILE": "click_count.json",
    "COUNTER_FONT_SIZE": 14,
    "COUNTER_TEXT_COLOR": [255, 255, 255],
    "COUNTER_BG_COLOR": [20, 20, 20],
    "COUNTER_BG_ALPHA": 180,
    "MESSAGE_FONT_SIZE": 16,
    "MESSAGE_TEXT_COLOR": [255, 255, 255],
    "MESSAGE_BG_COLOR": [30, 30, 30],
    "MESSAGE_BG_ALPHA": 210,
    "TRANS_COLOR": [12, 12, 12],
}

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    config = DEFAULT_CONFIG.copy()
    for k, v in loaded.items():
        if not k.startswith("_"):
            config[k] = v
else:
    config = DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

SCALE_FACTOR            = config["SCALE_FACTOR"]
PAW_L_X_OFFSET          = config["PAW_L_X_OFFSET"]
PAW_L_Y_OFFSET          = config["PAW_L_Y_OFFSET"]
PAW_R_X_OFFSET          = config["PAW_R_X_OFFSET"]
PAW_R_Y_OFFSET          = config["PAW_R_Y_OFFSET"]
PAW_BOUNCE_DISTANCE     = config["PAW_BOUNCE_DISTANCE"]
PAW_BOUNCE_FRAMES_KEY   = config["PAW_BOUNCE_FRAMES_KEY"]
PAW_BOUNCE_FRAMES_MOVE  = config["PAW_BOUNCE_FRAMES_MOUSE_MOVE"]
PAW_BOUNCE_FRAMES_CLICK = config["PAW_BOUNCE_FRAMES_MOUSE_CLICK"]
CLICK_MESSAGE           = config["CLICK_MESSAGE"]
CLICK_MESSAGE_DURATION  = config["CLICK_MESSAGE_DURATION_FRAMES"]
SHOW_COUNTER_ON_HOVER   = config["SHOW_COUNTER_ON_HOVER"]
COUNTER_SAVE_FILE       = get_path(config["COUNTER_SAVE_FILE"])
COUNTER_FONT_SIZE       = config["COUNTER_FONT_SIZE"]
COUNTER_TEXT_COLOR      = tuple(config["COUNTER_TEXT_COLOR"])
COUNTER_BG_COLOR        = tuple(config["COUNTER_BG_COLOR"])
COUNTER_BG_ALPHA        = config["COUNTER_BG_ALPHA"]
MESSAGE_FONT_SIZE       = config["MESSAGE_FONT_SIZE"]
MESSAGE_TEXT_COLOR      = tuple(config["MESSAGE_TEXT_COLOR"])
MESSAGE_BG_COLOR        = tuple(config["MESSAGE_BG_COLOR"])
MESSAGE_BG_ALPHA        = config["MESSAGE_BG_ALPHA"]
TRANS_COLOR             = tuple(config["TRANS_COLOR"])

# =====================================================================
# FIX #2: Dimensiunea ferestrei include spatiu extra pentru bounce.
# Corpul tigrului ramane la dimensiunea originala (BODY_HEIGHT).
# Spațiul extra de la baza ferestrei e transparent — laba coboara acolo.
# =====================================================================
HAS_SEPARATE_ASSETS = False
try:
    temp_img = pygame.image.load(get_path("body.png"))
    orig_w, orig_h = temp_img.get_size()
    HAS_SEPARATE_ASSETS = True
    print(f"\n{'='*55}")
    print(f"[GHID] body.png: {orig_w}x{orig_h} px | scale: {SCALE_FACTOR}")
    print(f" -> X_OFFSET 0-{orig_w}  |  Y_OFFSET 0-{orig_h}")
    print(f"{'='*55}\n")
except pygame.error:
    try:
        temp_img = pygame.image.load(get_path("tiger.png"))
        orig_w, orig_h = temp_img.get_size()
    except pygame.error:
        print(f"[EROARE] Nu s-a gasit body.png sau tiger.png in: {BASE_DIR}")
        sys.exit()

WIDTH       = int(orig_w * SCALE_FACTOR)
BODY_HEIGHT = int(orig_h * SCALE_FACTOR)

# Fereastra e mai inalta decat corpul cu PAW_BOUNCE_DISTANCE px.
# Zona extra e TRANS_COLOR (transparenta) => laba poate cobori oricand.
HEIGHT = BODY_HEIGHT + PAW_BOUNCE_DISTANCE

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Bongo Tiger")

if HAS_SEPARATE_ASSETS:
    img_body  = pygame.image.load(get_path("body.png")).convert_alpha()
    img_paw_l = pygame.image.load(get_path("paw_left.png")).convert_alpha()
    img_paw_r = pygame.image.load(get_path("paw_right.png")).convert_alpha()

    # Corp scalat la BODY_HEIGHT (nu HEIGHT) — spatiul extra ramane liber
    img_body  = pygame.transform.scale(img_body, (WIDTH, BODY_HEIGHT))
    img_paw_l = pygame.transform.scale(img_paw_l, (
        int(img_paw_l.get_width()  * SCALE_FACTOR),
        int(img_paw_l.get_height() * SCALE_FACTOR)
    ))
    img_paw_r = pygame.transform.scale(img_paw_r, (
        int(img_paw_r.get_width()  * SCALE_FACTOR),
        int(img_paw_r.get_height() * SCALE_FACTOR)
    ))
else:
    img_tiger = pygame.image.load(get_path("tiger.png")).convert_alpha()
    img_tiger = pygame.transform.scale(img_tiger, (WIDTH, BODY_HEIGHT))

# =====================================================================
# CONTORUL DE CLICK-URI (SALVARE / INCARCARE)
# FIX #1: Contorul e incrementat DOAR in event-ul pygame MOUSEBUTTONDOWN
#         adica numai cand dai click direct pe fereastra tigrului.
#         Listener-ii globali (tastatura / mouse global) NU ating contorul.
# =====================================================================
def load_click_count():
    if os.path.exists(COUNTER_SAVE_FILE):
        try:
            with open(COUNTER_SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("total_clicks", 0))
        except Exception:
            return 0
    return 0

def save_click_count(count):
    try:
        with open(COUNTER_SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump({"total_clicks": count}, f)
    except Exception as e:
        print(f"[WARN] Nu s-a putut salva contorul: {e}")

saved_clicks   = load_click_count()
session_clicks = 0

def on_exit():
    save_click_count(saved_clicks + session_clicks)

atexit.register(on_exit)

# =====================================================================
# FIX #3: ALWAYS ON TOP — SetWindowPos cu HWND_TOPMOST la pornire.
# SetWindowLong seteaza flag-ul, dar nu reordoneaza Z-order-ul imediat.
# SetWindowPos cu HWND_TOPMOST il forteaza pe loc.
# =====================================================================
if WINDOWS_OS:
    hwnd = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowLong(
        hwnd, win32con.GWL_EXSTYLE,
        win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        | win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST
    )
    win32gui.SetLayeredWindowAttributes(
        hwnd, win32api.RGB(*TRANS_COLOR), 0, win32con.LWA_COLORKEY
    )
    # Forteaza fereastra pe deasupra IMEDIAT la pornire
    win32gui.SetWindowPos(
        hwnd, win32con.HWND_TOPMOST,
        0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
    )

clock = pygame.time.Clock()

# =====================================================================
# FONTURI
# =====================================================================
font_counter = pygame.font.SysFont("Arial", COUNTER_FONT_SIZE, bold=True)
font_message = pygame.font.SysFont("Arial", MESSAGE_FONT_SIZE, bold=True)

# =====================================================================
# VARIABILE DE STARE
# =====================================================================
paw_l_timer         = 0
paw_r_timer         = 0
last_paw_alternated = "right"

dragging       = False
drag_offset_x  = 0
drag_offset_y  = 0

# Separam "mouse apasat" de "click contat" — drag-ul nu incrementeaza
mouse_down_pos  = None   # Pozitia la mousedown
click_msg_timer = 0
is_hovering     = False

CLICK_DRAG_THRESHOLD = 5  # Pixeli — miscare mai mica = click, mai mare = drag

# =====================================================================
# HELPERE DE DESENAT
# =====================================================================
def draw_alpha_box(surface, color_rgb, alpha, rect, radius=8):
    box = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(box, (*color_rgb, alpha), box.get_rect(), border_radius=radius)
    surface.blit(box, (rect.x, rect.y))

def draw_counter(surface):
    total = saved_clicks + session_clicks
    text  = f"{total:,}".replace(",", " ")
    surf  = font_counter.render(text, True, COUNTER_TEXT_COLOR)
    sw, sh = surf.get_size()
    cx = (WIDTH - sw) // 2
    cy = HEIGHT - sh - 8
    bg = pygame.Rect(cx - 10, cy - 5, sw + 20, sh + 10)
    draw_alpha_box(surface, COUNTER_BG_COLOR, COUNTER_BG_ALPHA, bg, radius=8)
    surface.blit(surf, (cx, cy))

def draw_click_message(surface, timer):
    fade_start = max(1, CLICK_MESSAGE_DURATION // 3)
    alpha = 255 if timer > fade_start else int(255 * timer / fade_start)
    alpha = max(0, min(255, alpha))

    surf = font_message.render(CLICK_MESSAGE, True, MESSAGE_TEXT_COLOR)
    sw, sh = surf.get_size()
    mx = (WIDTH - sw) // 2
    my = 12
    bg = pygame.Rect(mx - 10, my - 6, sw + 20, sh + 12)
    draw_alpha_box(surface, MESSAGE_BG_COLOR, int(MESSAGE_BG_ALPHA * alpha / 255), bg, radius=10)
    surf.set_alpha(alpha)
    surface.blit(surf, (mx, my))

# =====================================================================
# ASCULTATORI GLOBALI DE INPUT
# Toate tastele si click-urile (oriunde pe ecran) incrementeaza contorul
# si animeaza labele. Mesajul "Rawr" se afiseaza DOAR la click pe tigru.
# =====================================================================
def on_global_key_press(key):
    global paw_l_timer, paw_r_timer, last_paw_alternated, session_clicks
    session_clicks += 1   # Orice tasta apasata = +1
    if last_paw_alternated == "right":
        paw_l_timer = PAW_BOUNCE_FRAMES_KEY
        last_paw_alternated = "left"
    else:
        paw_r_timer = PAW_BOUNCE_FRAMES_KEY
        last_paw_alternated = "right"

def on_global_mouse_move(x, y):
    global paw_r_timer
    if not dragging:
        paw_r_timer = PAW_BOUNCE_FRAMES_MOVE

def on_global_mouse_click(x, y, button, pressed):
    global paw_r_timer, session_clicks
    if pressed and not dragging:
        session_clicks += 1   # Orice click oriunde pe ecran = +1
        paw_r_timer = PAW_BOUNCE_FRAMES_CLICK

kb_listener    = keyboard.Listener(on_press=on_global_key_press)
mouse_listener = mouse.Listener(
    on_move=on_global_mouse_move,
    on_click=on_global_mouse_click
)
kb_listener.start()
mouse_listener.start()

print(f"[INFO] Bongo Tiger pornit! Click-uri salvate: {saved_clicks}")
print(f"[INFO] ESC sau click dreapta pentru iesire.")

# =====================================================================
# BUCLA PRINCIPALA
# =====================================================================
running = True
while running:
    clock.tick(60)

    is_hovering = pygame.mouse.get_focused()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                dragging       = True
                drag_offset_x, drag_offset_y = event.pos
                mouse_down_pos = event.pos   # Salvam pozitia initiala
            elif event.button == 3:
                running = False

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                dragging = False
                # Mesajul "Rawr" apare DOAR la click direct pe tigru (nu drag)
                if mouse_down_pos is not None:
                    dx = abs(event.pos[0] - mouse_down_pos[0])
                    dy = abs(event.pos[1] - mouse_down_pos[1])
                    if dx <= CLICK_DRAG_THRESHOLD and dy <= CLICK_DRAG_THRESHOLD:
                        click_msg_timer = CLICK_MESSAGE_DURATION
                mouse_down_pos = None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # Misca fereastra cu drag; re-assert TOPMOST la fiecare miscare
    if dragging and WINDOWS_OS:
        gx, gy = win32gui.GetCursorPos()
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOPMOST,
            gx - drag_offset_x, gy - drag_offset_y,
            0, 0, win32con.SWP_NOSIZE
        )

    if paw_l_timer    > 0: paw_l_timer    -= 1
    if paw_r_timer    > 0: paw_r_timer    -= 1
    if click_msg_timer > 0: click_msg_timer -= 1

    # ---- DESENARE ----
    screen.fill(TRANS_COLOR)

    if HAS_SEPARATE_ASSETS:
        screen.blit(img_body, (0, 0))   # Corp la (0,0), inalt BODY_HEIGHT

        # FIX #2: Labele pornesc de la pozitia lor normala.
        # Bounce-ul le muta in jos in spatiul transparent extra (HEIGHT - BODY_HEIGHT).
        # Nu pot iesi niciodata din fereastra.
        offset_l = PAW_BOUNCE_DISTANCE if paw_l_timer > 0 else 0
        offset_r = PAW_BOUNCE_DISTANCE if paw_r_timer > 0 else 0

        screen.blit(img_paw_l, (
            int(PAW_L_X_OFFSET * SCALE_FACTOR),
            int(PAW_L_Y_OFFSET * SCALE_FACTOR) + offset_l
        ))
        screen.blit(img_paw_r, (
            int(PAW_R_X_OFFSET * SCALE_FACTOR),
            int(PAW_R_Y_OFFSET * SCALE_FACTOR) + offset_r
        ))
    else:
        screen.blit(img_tiger, (0, 0))

    if click_msg_timer > 0:
        draw_click_message(screen, click_msg_timer)

    if is_hovering and SHOW_COUNTER_ON_HOVER:
        draw_counter(surface=screen)

    pygame.display.update()

# =====================================================================
# CLEANUP & SAVE
# =====================================================================
kb_listener.stop()
mouse_listener.stop()
save_click_count(saved_clicks + session_clicks)
print(f"[INFO] Salvat! Total click-uri: {saved_clicks + session_clicks}")
pygame.quit()
sys.exit()
