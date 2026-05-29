# main.py

import pygame
import sys
from scripts.game_manager import GameManager
from scripts.player       import Player
from scripts.lobby        import Lobby
from scripts.stage1       import Stage1

pygame.init()

# ── 고정 가상 해상도 (게임 로직은 항상 이 크기로 동작) ──
BASE_W, BASE_H = 800, 600

screen = pygame.display.set_mode((BASE_W, BASE_H))
pygame.display.set_caption("Soul Knight")
is_fullscreen = False

# 가상 캔버스: 게임 월드(타일·스프라이트 등)를 여기에 그린다
canvas = pygame.Surface((BASE_W, BASE_H))


def toggle_fullscreen():
    global screen, is_fullscreen
    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((BASE_W, BASE_H))


def get_scale_and_offset():
    """
    canvas를 screen에 letterbox 방식으로 맞출 때의
    (scale, offset_x, offset_y) 를 반환한다.
    """
    sw, sh = screen.get_size()
    scale  = min(sw / BASE_W, sh / BASE_H)
    ox     = (sw - BASE_W * scale) / 2
    oy     = (sh - BASE_H * scale) / 2
    return scale, ox, oy


def screen_to_canvas(mouse_pos):
    """실제 화면 마우스 좌표 → 가상 캔버스 좌표로 변환"""
    scale, ox, oy = get_scale_and_offset()
    cx = (mouse_pos[0] - ox) / scale
    cy = (mouse_pos[1] - oy) / scale
    return (int(cx), int(cy))


def scaled_font(base_size):
    """전체화면 배율에 맞게 폰트 크기를 조정하여 반환"""
    scale, _, _ = get_scale_and_offset()
    return pygame.font.SysFont(None, max(10, int(base_size * scale)))


def canvas_to_screen(cx, cy):
    """캔버스 좌표 → 실제 화면 좌표로 변환 (UI 직접 렌더링용)"""
    scale, ox, oy = get_scale_and_offset()
    return (int(cx * scale + ox), int(cy * scale + oy))


clock = pygame.time.Clock()

# ── 게임 오브젝트 ──────────────────────────────────────────
gm     = GameManager()
player = Player()
lobby  = Lobby(player)
stage1 = None   # 스테이지는 STAGE1 진입 시 생성


def new_stage():
    global stage1
    stage1 = Stage1(player)


# ── 화면 함수: canvas 대신 screen에 직접 그려 선명한 텍스트 ──
def draw_gameover(gm):
    sw, sh = screen.get_size()
    screen.fill((10, 5, 15))
    font1 = scaled_font(80)
    font2 = scaled_font(34)
    t1 = font1.render("GAME  OVER", True, (220, 50, 50))
    t2 = font2.render(f"Score: {gm.score}    Coins: {gm.coins}", True, (180, 160, 200))
    t3 = font2.render("Press  R  to return to Lobby", True, (140, 130, 160))
    screen.blit(t1, (sw//2 - t1.get_width()//2, int(sh * 0.33)))
    screen.blit(t2, (sw//2 - t2.get_width()//2, int(sh * 0.52)))
    screen.blit(t3, (sw//2 - t3.get_width()//2, int(sh * 0.62)))


def draw_clear(gm):
    sw, sh = screen.get_size()
    screen.fill((5, 15, 10))
    font1 = scaled_font(80)
    font2 = scaled_font(34)
    t1 = font1.render("STAGE  CLEAR!", True, (100, 255, 160))
    t2 = font2.render(f"Score: {gm.score}    Coins: {gm.coins}", True, (200, 240, 210))
    t3 = font2.render("Press  R  to return to Lobby", True, (140, 180, 150))
    screen.blit(t1, (sw//2 - t1.get_width()//2, int(sh * 0.33)))
    screen.blit(t2, (sw//2 - t2.get_width()//2, int(sh * 0.52)))
    screen.blit(t3, (sw//2 - t3.get_width()//2, int(sh * 0.62)))


# ── 메인 루프 ─────────────────────────────────────────────
running = True

while running:

    clock.tick(60)

    scale, ox, oy = get_scale_and_offset()

    # ── 이벤트 처리 ──────────────────────────────────────
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_F11:
                toggle_fullscreen()

            if event.key == pygame.K_ESCAPE:
                if gm.state == "STAGE1":
                    gm.state = "LOBBY"
                elif gm.state == "LOBBY":
                    running = False   # 로비에서 ESC → 종료

            if event.key == pygame.K_r:
                if gm.state in ("GAMEOVER", "CLEAR"):
                    player.hp = player.max_hp
                    gm.state  = "LOBBY"

        # 마우스 이벤트의 pos를 캔버스 좌표로 변환
        if event.type == pygame.MOUSEBUTTONDOWN:
            canvas_pos = screen_to_canvas(event.pos)
            event = pygame.event.Event(
                event.type,
                {**event.__dict__, "pos": canvas_pos}
            )

        # 상태별 이벤트 전달
        if gm.state == "LOBBY":
            lobby.handle_event(event, gm)
            if gm.state == "STAGE1":
                new_stage()

        elif gm.state == "STAGE1" and stage1:
            stage1.handle_event(event, gm)

    # ── 업데이트 & 그리기 ─────────────────────────────────
    keys = pygame.key.get_pressed()

    # 마우스를 캔버스 좌표로 변환
    mouse_pos = screen_to_canvas(pygame.mouse.get_pos())

    # ── canvas에 게임 월드(타일·스프라이트 등) 그리기 ─────
    if gm.state == "LOBBY":
        lobby.update(keys)
        lobby.draw(canvas, gm)

    elif gm.state == "STAGE1" and stage1:
        stage1.update(keys, mouse_pos, gm)
        stage1.draw(canvas, gm)

    # ── canvas → screen 스케일링 (최근접 보간으로 픽셀 유지) ─
    if gm.state in ("LOBBY", "STAGE1"):
        if scale == 1.0 and ox == 0 and oy == 0:
            screen.blit(canvas, (0, 0))
        else:
            screen.fill((0, 0, 0))
            scaled = pygame.transform.scale(
                canvas,
                (int(BASE_W * scale), int(BASE_H * scale))
            )
            screen.blit(scaled, (int(ox), int(oy)))

    # ── UI 텍스트는 screen에 직접 그려 선명하게 유지 ──────
    elif gm.state == "GAMEOVER":
        draw_gameover(gm)

    elif gm.state == "CLEAR":
        draw_clear(gm)

    pygame.display.flip()

pygame.quit()
sys.exit()