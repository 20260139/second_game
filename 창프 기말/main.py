# main.py

import pygame
import sys
from scripts.game_manager import GameManager
from scripts.player       import Player
from scripts.lobby        import Lobby
from scripts.stage1       import Stage1

pygame.init()

SW, SH = 800, 600
screen = pygame.display.set_mode((SW, SH))
pygame.display.set_caption("Soul Knight")
is_fullscreen = False


def toggle_fullscreen():
    global screen, SW, SH, is_fullscreen
    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((800, 600))
    SW, SH = screen.get_size()
clock  = pygame.time.Clock()

# ── 게임 오브젝트 ──────────────────────────────────────────
gm     = GameManager()
player = Player()
lobby  = Lobby(player)
stage1 = None   # 스테이지는 STAGE1 진입 시 생성


def new_stage():
    global stage1
    stage1 = Stage1(player)


# ── 화면 함수 ─────────────────────────────────────────────
def draw_gameover(screen, gm):
    sw = screen.get_width()
    screen.fill((10, 5, 15))
    font1 = pygame.font.SysFont(None, 80)
    font2 = pygame.font.SysFont(None, 34)
    t1 = font1.render("GAME  OVER", True, (220, 50, 50))
    t2 = font2.render(f"Score: {gm.score}    Coins: {gm.coins}", True, (180, 160, 200))
    t3 = font2.render("Press  R  to return to Lobby", True, (140, 130, 160))
    screen.blit(t1, (sw//2 - t1.get_width()//2, 200))
    screen.blit(t2, (sw//2 - t2.get_width()//2, 310))
    screen.blit(t3, (sw//2 - t3.get_width()//2, 370))


def draw_clear(screen, gm):
    sw = screen.get_width()
    screen.fill((5, 15, 10))
    font1 = pygame.font.SysFont(None, 80)
    font2 = pygame.font.SysFont(None, 34)
    t1 = font1.render("STAGE  CLEAR!", True, (100, 255, 160))
    t2 = font2.render(f"Score: {gm.score}    Coins: {gm.coins}", True, (200, 240, 210))
    t3 = font2.render("Press  R  to return to Lobby", True, (140, 180, 150))
    screen.blit(t1, (sw//2 - t1.get_width()//2, 200))
    screen.blit(t2, (sw//2 - t2.get_width()//2, 310))
    screen.blit(t3, (sw//2 - t3.get_width()//2, 370))


# ── 메인 루프 ─────────────────────────────────────────────
running = True

while running:

    clock.tick(60)

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
                    # 로비로 돌아가기 (HP 복구)
                    player.hp = player.max_hp
                    gm.state  = "LOBBY"

        # 상태별 이벤트 전달
        if gm.state == "LOBBY":
            lobby.handle_event(event, gm)
            if gm.state == "STAGE1":   # 방금 입장
                new_stage()

        elif gm.state == "STAGE1" and stage1:
            stage1.handle_event(event, gm)

    # ── 업데이트 & 그리기 ─────────────────────────────────
    keys      = pygame.key.get_pressed()
    mouse_pos = pygame.mouse.get_pos()

    if gm.state == "LOBBY":
        lobby.update(keys)
        lobby.draw(screen, gm)   # gm 직접 전달

    elif gm.state == "STAGE1" and stage1:
        stage1.update(keys, mouse_pos, gm)
        stage1.draw(screen, gm)

    elif gm.state == "GAMEOVER":
        draw_gameover(screen, gm)

    elif gm.state == "CLEAR":
        draw_clear(screen, gm)

    pygame.display.flip()

pygame.quit()
sys.exit()
