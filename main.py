import pygame
import sys
import threading
import os
from pynput import keyboard, mouse

try:
    import win32api
    import win32con
    import win32gui
    WINDOWS_OS = True
except ImportError:
    WINDOWS_OS = False

pygame.init()

# =====================================================================
# GAME CONFIGURATION
# =====================================================================
SCALE_FACTOR = 0.2  # 1.0 = 1.0 = full size, 0.5 = half, 0.3 = small, etc.

PAW_L_X_OFFSET = 0   
PAW_L_Y_OFFSET = 280  

PAW_R_X_OFFSET = 351  
PAW_R_Y_OFFSET = 280 
# =====================================================================

TRANS_COLOR = (12, 12, 12)  # Key color for transparency

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_path(filename):
    return os.path.join(BASE_DIR, filename)

# --- STEP 1: FIND OUT THE ORIGINAL SIZE AND DISPLAY THE GUIDE ---
HAS_SEPARATE_ASSETS = False
try:
    temp_img = pygame.image.load(get_path("body.png"))
    orig_w, orig_h = temp_img.get_size()
    HAS_SEPARATE_ASSETS = True
    
    # GHID EXPLICATIV ÎN CONSOLĂ
    print("\n" + "="*60)
    print(f"[GHID] Imaginea ta 'body.png' are dimensiunea de: {orig_w}x{orig_h} pixeli.")
    print(f" -> Pentru a mișca lăbuțele la stânga/dreapta, setează X_OFFSET între 0 și {orig_w}")
    print(f" -> Pentru a le coborî de pe ochi spre masă, setează Y_OFFSET între 0 și {orig_h}")
    print("="*60 + "\n")
    
except pygame.error:
    try:
        temp_img = pygame.image.load(get_path("tiger.png"))
        orig_w, orig_h = temp_img.get_size()
    except pygame.error:
        print(f"\n[EROARE] Nu s-a găsit nici body.png, nici tiger.png în folderul: {BASE_DIR}")
        sys.exit()

# --- STEP 2: INITIALIZE THE WINDOW ---
WIDTH = int(orig_w * SCALE_FACTOR)
HEIGHT = int(orig_h * SCALE_FACTOR)
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Bongo Tiger 🐯")

# --- STEP 3: WE UPLOAD IMAGES SECURELY ---
if HAS_SEPARATE_ASSETS:
    img_body = pygame.image.load(get_path("body.png")).convert_alpha()
    img_paw_l = pygame.image.load(get_path("paw_left.png")).convert_alpha()
    img_paw_r = pygame.image.load(get_path("paw_right.png")).convert_alpha()
    
# Scale the elements proportionally
    img_body = pygame.transform.scale(img_body, (WIDTH, HEIGHT))
    img_paw_l = pygame.transform.scale(img_paw_l, (int(img_paw_l.get_width() * SCALE_FACTOR), int(img_paw_l.get_height() * SCALE_FACTOR)))
    img_paw_r = pygame.transform.scale(img_paw_r, (int(img_paw_r.get_width() * SCALE_FACTOR), int(img_paw_r.get_height() * SCALE_FACTOR)))
else:
    img_tiger = pygame.image.load(get_path("tiger.png")).convert_alpha()
    img_tiger = pygame.transform.scale(img_tiger, (WIDTH, HEIGHT))

# --- ENABLE WINDOWS TRANSPARENCY ---
if WINDOWS_OS:
    hwnd = pygame.display.get_wm_info()["window"]
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, 
                           win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | 
                           win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST)
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*TRANS_COLOR), 0, win32con.LWA_COLORKEY)

clock = pygame.time.Clock()

# --- ANIMATION & MOTION VARIABLES ---
paw_l_timer = 0
paw_r_timer = 0
last_paw_alternated = "right"

dragging = False
drag_offset_x = 0
drag_offset_y = 0

# --- GLOBAL INPUTS LISTENERS (Background) ---
def on_global_key_press(key):
    global paw_l_timer, paw_r_timer, last_paw_alternated
    if last_paw_alternated == "right":
        paw_l_timer = 5  
        last_paw_alternated = "left"
    else:
        paw_r_timer = 5  
        last_paw_alternated = "right"

def on_global_mouse_move(x, y):
    global paw_r_timer
    if not dragging:  
        paw_r_timer = 3  

def on_global_mouse_click(x, y, button, pressed):
    global paw_r_timer
    if pressed and not dragging:
        paw_r_timer = 7  

kb_listener = keyboard.Listener(on_press=on_global_key_press)
kb_listener.start()

mouse_listener = mouse.Listener(on_move=on_global_mouse_move, on_click=on_global_mouse_click)
mouse_listener.start()

# --- MAIN LOOP ---
running = True
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Drag & Drop logic for moving the window on the screen
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  
                dragging = True
                drag_offset_x, drag_offset_y = event.pos
        
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                dragging = False
                
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:  
                running = False

    # Moving the tiger on the screen
    if dragging and WINDOWS_OS:
        gx, gy = win32gui.GetCursorPos()
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, gx - drag_offset_x, gy - drag_offset_y, 0, 0, win32con.SWP_NOSIZE)

    if paw_l_timer > 0: paw_l_timer -= 1
    if paw_r_timer > 0: paw_r_timer -= 1

    screen.fill(TRANS_COLOR)

    if HAS_SEPARATE_ASSETS:
        screen.blit(img_body, (0, 0))

        bounce_dist = int(15 * SCALE_FACTOR)
        offset_l = bounce_dist if paw_l_timer > 0 else 0
        offset_r = bounce_dist if paw_r_timer > 0 else 0

        screen.blit(img_paw_l, (int(PAW_L_X_OFFSET * SCALE_FACTOR), int(PAW_L_Y_OFFSET * SCALE_FACTOR) + offset_l))
        screen.blit(img_paw_r, (int(PAW_R_X_OFFSET * SCALE_FACTOR), int(PAW_R_Y_OFFSET * SCALE_FACTOR) + offset_r))
    else:
        screen.blit(img_tiger, (0, 0))

    pygame.display.update()

pygame.quit()
sys.exit()