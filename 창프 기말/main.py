# main.py

import pygame

from scripts.game_manager import GameManager
from scripts.stage1       import Stage1
from scripts.player       import Player

pygame.init()

SCREEN_W = 800
SCREEN_H = 600

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Boss Rush")

clock   = pygame.time.Clock()
font    = pygame.font.SysFont(None, 42)
font_sm = pygame.font.SysFont(None, 28)

gm     = GameManager()
stage1 = Stage1()
player = Player()
player.x, player.y = stage1.player_start

# ── 카메라 ────────────────────────────────────────────────
cam_x = 0.0
cam_y = 0.0


def update_camera(px, py, map_w, map_h):
    global cam_x, cam_y
    target_x = px - SCREEN_W * 0.35          # 플레이어 약간 왼쪽 배치
    target_y = py - SCREEN_H * 0.55
    target_x = max(0, min(target_x, map_w - SCREEN_W))
    target_y = max(0, min(target_y, map_h - SCREEN_H))
    cam_x += (target_x - cam_x) * 0.10
    cam_y += (target_y - cam_y) * 0.10


# ── 랭킹 ─────────────────────────────────────────────────
def save_ranking(clear_time):
    rankings = []
    try:
        with open("data/ranking.txt", "r") as f:
            for line in f:
                rankings.append(float(line.strip()))
    except:
        pass
    rankings.append(clear_time)
    rankings.sort()
    rankings = rankings[:10]
    try:
        with open("data/ranking.txt", "w") as f:
            for r in rankings:
                f.write(f"{r}\n")
    except:
        pass


def load_ranking():
    rankings = []
    try:
        with open("data/ranking.txt", "r") as f:
            for line in f:
                rankings.append(float(line.strip()))
    except:
        pass
    return rankings


saved   = False
running = True

while running:

    clock.tick(60)

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            # 시작
            if gm.state == "START":
                if event.key == pygame.K_SPACE:
                    gm.start_game()

            # 점프 (이벤트로 처리 → 1번만 발동)
            elif gm.state == "STAGE1":
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_SPACE):
                    player.jump()

            elif gm.state == "STAGE2":
                if event.key == pygame.K_2:
                    gm.next_stage()

            elif gm.state == "STAGE3":
                if event.key == pygame.K_3:
                    gm.next_stage()

            # 즉사 (테스트)
            if event.key == pygame.K_q:
                gm.game_over()

        # 마우스 좌클릭 이벤트 → 공격 (이벤트 기반이므로 클릭 1번 = 공격 1번)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if gm.state == "STAGE1":
                player.on_mouse_click(event.button)

    # ═══════════════════════════════════════════════════
    #  시작 화면
    # ═══════════════════════════════════════════════════
    if gm.state == "START":

        screen.fill((18, 18, 30))

        title = font.render("BOSS  RUSH", True, (255, 210, 50))
        sub   = font_sm.render("PRESS  SPACE  TO  START", True, (200, 200, 200))
        ctrl  = font_sm.render(
            "A / D : Move    W / Space : Jump    LClick : Attack",
            True, (140, 140, 160)
        )

        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 210))
        screen.blit(sub,   (SCREEN_W // 2 - sub.get_width()   // 2, 295))
        screen.blit(ctrl,  (SCREEN_W // 2 - ctrl.get_width()  // 2, 370))

    # ═══════════════════════════════════════════════════
    #  스테이지 1
    # ═══════════════════════════════════════════════════
    elif gm.state == "STAGE1":

        keys = pygame.key.get_pressed()
        player.input(keys)
        player.update(stage1.platforms)
        stage1.update()

        update_camera(player.x, player.y,
                      stage1.map_width, stage1.map_height)

        # ── 그리기 ──
        stage1.draw(screen, cam_x, cam_y, SCREEN_W, SCREEN_H)
        player.draw(screen, int(cam_x), int(cam_y))

        # ── 충돌: 용암 ──
        prect = player.get_rect()
        for lava in stage1.lavas:
            if prect.colliderect(lava):
                player.damage(2)

        # ── 충돌: 가시 ──
        for spike in stage1.spikes:
            if prect.colliderect(spike):
                player.damage(3)

        # ── 충돌: 레이저 ──
        for laser in stage1.lasers:
            if laser.active and prect.colliderect(laser.rect):
                player.damage(2)

        # ── 낙사 판정 ──
        if player.y > stage1.map_height + 100:
            player.damage(999)

        # ── HP 0 → 게임오버 ──
        if player.hp <= 0:
            gm.game_over()

        # ── 출구 도달 → 다음 스테이지 ──
        if prect.colliderect(stage1.goal):
            gm.next_stage()

        # ── HUD ──
        player.draw_hud(screen)
        stage1.draw_minimap(screen, player.x, player.y, SCREEN_W)

        timer_text = font_sm.render(
            f"TIME : {gm.get_time():.2f}", True, (220, 220, 220)
        )
        screen.blit(timer_text, (20, 40))

        hint = font_sm.render(
            "→ Reach the GOLD DOOR", True, (200, 180, 60)
        )
        screen.blit(hint, (20, SCREEN_H - 28))

    # ═══════════════════════════════════════════════════
    #  스테이지 2 (플레이스홀더)
    # ═══════════════════════════════════════════════════
    elif gm.state == "STAGE2":

        screen.fill((20, 20, 32))
        t1 = font.render("STAGE  2", True, (255, 255, 255))
        t2 = font_sm.render(f"TIME : {gm.get_time():.2f}", True, (200, 200, 200))
        t3 = font_sm.render("PRESS  2  →  STAGE 3", True, (160, 160, 160))
        screen.blit(t1, (SCREEN_W // 2 - t1.get_width() // 2, 210))
        screen.blit(t2, (20, 20))
        screen.blit(t3, (SCREEN_W // 2 - t3.get_width() // 2, 300))

    # ═══════════════════════════════════════════════════
    #  스테이지 3 (플레이스홀더)
    # ═══════════════════════════════════════════════════
    elif gm.state == "STAGE3":

        screen.fill((20, 20, 32))
        t1 = font.render("STAGE  3", True, (255, 255, 255))
        t2 = font_sm.render(f"TIME : {gm.get_time():.2f}", True, (200, 200, 200))
        t3 = font_sm.render("PRESS  3  →  CLEAR", True, (160, 160, 160))
        screen.blit(t1, (SCREEN_W // 2 - t1.get_width() // 2, 210))
        screen.blit(t2, (20, 20))
        screen.blit(t3, (SCREEN_W // 2 - t3.get_width() // 2, 300))

    # ═══════════════════════════════════════════════════
    #  클리어
    # ═══════════════════════════════════════════════════
    elif gm.state == "CLEAR":

        if not saved:
            save_ranking(gm.clear_time)
            saved = True

        screen.fill((18, 18, 30))
        t1 = font.render("GAME  CLEAR !!", True, (255, 220, 50))
        t2 = font_sm.render(f"CLEAR TIME : {gm.clear_time:.2f} sec", True, (255, 255, 255))
        screen.blit(t1, (SCREEN_W // 2 - t1.get_width() // 2, 55))
        screen.blit(t2, (SCREEN_W // 2 - t2.get_width() // 2, 110))

        rt = font_sm.render("─── RANKING ───", True, (180, 180, 180))
        screen.blit(rt, (SCREEN_W // 2 - rt.get_width() // 2, 155))

        rankings = load_ranking()
        for i in range(10):
            txt   = f"  {i+1}.  {rankings[i]:.2f} sec" if i < len(rankings) else f"  {i+1}."
            color = (255, 210, 50) if i == 0 else (190, 190, 190)
            r     = font_sm.render(txt, True, color)
            screen.blit(r, (SCREEN_W // 2 - 80, 188 + i * 30))

    # ═══════════════════════════════════════════════════
    #  게임오버
    # ═══════════════════════════════════════════════════
    elif gm.state == "GAMEOVER":

        screen.fill((18, 10, 10))
        t1 = font.render("GAME  OVER", True, (220, 50, 50))
        t2 = font_sm.render("TIME NOT SAVED", True, (170, 170, 170))
        screen.blit(t1, (SCREEN_W // 2 - t1.get_width() // 2, 250))
        screen.blit(t2, (SCREEN_W // 2 - t2.get_width() // 2, 315))

    pygame.display.update()

pygame.quit()
