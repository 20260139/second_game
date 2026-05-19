# scripts/stage1.py

import pygame
from scripts.laser import Laser


class Stage1:

    def __init__(self):

        self.map_width  = 3600
        self.map_height = 600

        # ══════════════════════════════════════════════════
        #  플랫폼  (x, y, w, h)
        #  구역 구분:
        #   A  시작     x   0 ~  600
        #   B  발판점프 x 600 ~ 1100
        #   C  레이저벽 x1100 ~ 1700   ← 레이저가 통로를 막음
        #   D  낙하구멍 x1700 ~ 2300
        #   E  상승계단 x2300 ~ 2900
        #   F  보스전실 x2900 ~ 3600
        # ══════════════════════════════════════════════════
        self.platforms = [

            # ── A: 시작 구역 ──────────────────────────────
            pygame.Rect(   0, 520, 620,  20),   # 바닥
            pygame.Rect(   0,   0,  20, 600),   # 왼쪽 벽
            pygame.Rect(   0,   0, 620,  20),   # 위쪽 천장 (A전체 막기)

            # ── B: 점프 발판 구역 ─────────────────────────
            # 위쪽을 막는 천장 (y=0): A 천장이 맵 전체 위를 막음
            pygame.Rect(   0,   0,3600,  20),   # 맵 전체 상단 천장

            pygame.Rect( 620, 472,  80,  16),   # B 발판 1  (y=520-48=472)
            pygame.Rect( 740, 410,  80,  16),   # B 발판 2
            pygame.Rect( 860, 350,  80,  16),   # B 발판 3
            pygame.Rect( 980, 410,  80,  16),   # B 발판 4
            pygame.Rect(1080, 472,  80,  16),   # B 발판 5 (C 바닥과 같은 높이)

            # ── C: 레이저 터널 ────────────────────────────
            # 기둥/천장 없음 → 레이저만 막음
            # 바닥은 B 마지막 발판과 이어짐
            pygame.Rect(1160, 520, 540,  20),   # C 바닥 (입구~출구)

            # 피난 발판 (레이저 사이, 바닥보다 높게)
            pygame.Rect(1310, 456,  60,  16),   # 피난 발판 1
            pygame.Rect(1450, 456,  60,  16),   # 피난 발판 2
            pygame.Rect(1570, 456,  60,  16),   # 피난 발판 3

            # ── D: 낙하 구멍 구역 ─────────────────────────
            pygame.Rect(1700, 520, 100,  20),   # 입구 발판
            pygame.Rect(1860, 520,  80,  20),   # 발판 1
            pygame.Rect(2000, 480,  80,  20),   # 발판 2
            pygame.Rect(2130, 520,  80,  20),   # 발판 3
            pygame.Rect(2250, 480,  80,  20),   # 발판 4

            # ── E: 상승 계단 구역 ─────────────────────────
            pygame.Rect(2340, 520,  80,  20),
            pygame.Rect(2440, 460,  80,  16),
            pygame.Rect(2540, 400,  80,  16),
            pygame.Rect(2640, 340,  80,  16),
            pygame.Rect(2740, 280,  80,  16),
            pygame.Rect(2840, 220,  80,  16),

            # ── F: 보스 전실 ──────────────────────────────
            pygame.Rect(2920, 580, 680,  20),   # 하단 바닥
            pygame.Rect(2920, 240,  20, 340),   # 왼쪽 벽
            pygame.Rect(3580, 240,  20, 340),   # 오른쪽 벽

            # 내부 발판
            pygame.Rect(3000, 460,  80,  16),
            pygame.Rect(3150, 380,  80,  16),
            pygame.Rect(3300, 460,  80,  16),
            pygame.Rect(3430, 380,  80,  16),
        ]

        # ══════════════════════════════════════════════════
        #  용암 / 구멍 (데미지 영역)
        # ══════════════════════════════════════════════════
        self.lavas = [
            # C구역 레이저 터널 바닥 용암
            # 피난 발판 사이사이 (바닥 y=520 위 y=520~540)
            pygame.Rect(1220, 520,  90, 20),   # 입구~발판1 사이
            pygame.Rect(1370, 520,  80, 20),   # 발판1~2 사이
            pygame.Rect(1510, 520,  60, 20),   # 발판2~3 사이
            pygame.Rect(1630, 520,  70, 20),   # 발판3~출구 사이

            # D구역 구멍 사이 용암
            pygame.Rect(1800, 540,  60, 60),
            pygame.Rect(1940, 540,  60, 60),
            pygame.Rect(2080, 540,  50, 60),
            pygame.Rect(2210, 540,  40, 60),

            # E구역 계단 사이 용암
            pygame.Rect(2350, 540,  90, 60),
        ]

        # ══════════════════════════════════════════════════
        #  가시
        # ══════════════════════════════════════════════════
        self.spikes = [
            # B구역 발판 사이 바닥 (떨어지면 가시)
            pygame.Rect( 700, 540, 380, 10),

            # E구역 계단 아래
            pygame.Rect(2440, 540, 400, 10),

            # F구역 하단 바닥 일부
            pygame.Rect(3050, 568, 200, 12),
            pygame.Rect(3350, 568, 150, 12),
        ]

        # ══════════════════════════════════════════════════
        #  레이저 — C구역 터널 안에 배치
        #  세로 레이저: 통로를 수직으로 막음
        #  간격을 서로 다르게 → 타이밍 필요
        # ══════════════════════════════════════════════════
        # Laser(x, y, w, h, interval)
        # 세로 레이저: w=8, h=180 (바닥~천장)
        # active 시 충돌 → 비활성 때만 통과 가능
        self.lasers = [
            # C구역 세로 레이저 (y=340~520 → 바닥~맵상단 열린 공간 막기)
            # 바닥(y=520)부터 위로 h=180 → y=340~520
            Laser(1250, 340, 8, 180, 40),   # 1번 (빠름)
            Laser(1370, 340, 8, 180, 70),   # 2번 (느림)
            Laser(1490, 340, 8, 180, 50),   # 3번 (중간)
            Laser(1610, 340, 8, 180, 30),   # 4번 (매우 빠름)

            # F구역 수평 레이저 (하단 바닥 y=580 기준)
            Laser(2940, 480, 640, 8,  80),  # 수평 상단
            Laser(2940, 540, 640, 8,  55),  # 수평 하단
        ]

        # 출구: F구역 하단 바닥 오른쪽 끝
        self.goal = pygame.Rect(3530, 516, 44, 64)

        self.player_start = (60, 430)

    # ── 업데이트 ─────────────────────────────────────────
    def update(self):
        for laser in self.lasers:
            laser.update()

    # ── 그리기 ───────────────────────────────────────────
    def draw(self, screen, cam_x, cam_y, screen_w, screen_h):

        cx   = int(cam_x)
        cy   = int(cam_y)
        tick = pygame.time.get_ticks()

        # ── 하늘 그라데이션 ──
        for row in range(screen_h):
            t = row / screen_h
            r = int(18  + 40 * (1 - t))
            g = int(18  + 55 * (1 - t))
            b = int(35  + 90 * (1 - t))
            pygame.draw.line(screen, (r, g, b), (0, row), (screen_w, row))

        # ── 패럴랙스 구름 ──
        for bx, by in [(80,70),(220,50),(440,80),(600,60),(780,75)]:
            ox  = (bx - int(cam_x * 0.18)) % (screen_w + 120) - 60
            s   = pygame.Surface((110, 34), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (255, 255, 255, 50), (0, 0, 110, 34))
            screen.blit(s, (ox, by))

        # ── 패럴랙스 빌딩 ──
        bld = [(0,180,70,340),(90,150,55,370),(180,200,80,320),
               (300,170,65,350),(400,130,55,390),(510,190,75,330),
               (620,160,60,360),(730,200,70,320)]
        bc  = [(40,42,58),(50,48,65),(36,42,55)]
        for i,(bx,by,bw,bh) in enumerate(bld):
            ox = (bx - int(cam_x * 0.38)) % (screen_w + 160) - 80
            pygame.draw.rect(screen, bc[i%3], (ox,by,bw,bh))
            for wy in range(by+18, by+bh-18, 28):
                for wx in range(ox+8, ox+bw-8, 18):
                    pygame.draw.rect(screen, (55, 55, 70), (wx, wy, 7, 9))

        # ── 원경 지면 ──
        gy = screen_h - 60 - (cy % (screen_h))
        pygame.draw.rect(screen, (28,50,28), (0, max(gy,0), screen_w, screen_h))

        # ── C구역 터널 배경 표시 ──
        tunnel_rect = pygame.Rect(1200 - cx, 320 - cy, 500, 220)
        if tunnel_rect.right > 0 and tunnel_rect.left < screen_w:
            ts = pygame.Surface((500, 220), pygame.SRCALPHA)
            ts.fill((10, 10, 20, 160))
            screen.blit(ts, (tunnel_rect.x, tunnel_rect.y))

        # ── 플랫폼 ──
        for p in self.platforms:
            r = p.move(-cx, -cy)
            if r.right < 0 or r.left > screen_w:
                continue
            pygame.draw.rect(screen, (100, 112, 128), r, border_radius=2)
            pygame.draw.rect(screen, (65,  75,  92), pygame.Rect(r.x, r.y+5, r.w, r.h-5), border_radius=2)
            pygame.draw.line(screen, (155, 168, 185), (r.x+2, r.y+1), (r.x+r.w-2, r.y+1))

        # ── 용암 ──
        pulse = int(18 * abs(((tick // 75) % 20) - 10) / 10)
        for lv in self.lavas:
            r = lv.move(-cx, -cy)
            pygame.draw.rect(screen, (195+pulse, 52, 0), r)
            pygame.draw.rect(screen, (255, 115+pulse, 0), r, 2)
            for i in range(3):
                bxo = (tick//180 + i*38) % max(r.w, 1)
                byo = r.h//2 + int(4*((tick//140+i)%2 - 0.5)*2)
                pygame.draw.circle(screen, (255,130,15), (r.x+bxo, r.y+byo), 3)

        # ── 가시 ──
        for sp in self.spikes:
            r  = sp.move(-cx, -cy)
            sw = 12
            for sx in range(r.x, r.x + r.w, sw):
                mid = sx + sw // 2
                pygame.draw.polygon(screen, (190, 50, 50),
                                    [(sx, r.bottom), (mid, r.top), (sx+sw, r.bottom)])

        # ── 레이저 ──
        for laser in self.lasers:
            r = laser.rect.move(-cx, -cy)
            if r.right < 0 or r.left > screen_w:
                continue
            if laser.active:
                pygame.draw.rect(screen, (0, 210, 255), r)
                # 글로우
                g2 = r.inflate(8, 8)
                gs = pygame.Surface((g2.w, g2.h), pygame.SRCALPHA)
                pygame.draw.rect(gs, (0, 210, 255, 45), gs.get_rect(), border_radius=4)
                screen.blit(gs, (g2.x, g2.y))
                # 경고선 (레이저 끝 점)
                pygame.draw.circle(screen, (255,255,255), (r.centerx, r.top), 4)
                pygame.draw.circle(screen, (255,255,255), (r.centerx, r.bottom), 4)
            else:
                # 비활성 상태: 어두운 점선으로 경고 표시
                step = 12
                for i in range(0, max(r.h, r.w), step*2):
                    if r.w > r.h:   # 수평
                        pygame.draw.line(screen, (0, 80, 120),
                                         (r.x+i, r.centery), (r.x+i+step, r.centery), 3)
                    else:           # 수직
                        pygame.draw.line(screen, (0, 80, 120),
                                         (r.centerx, r.y+i), (r.centerx, r.y+i+step), 3)

        # ── 출구 ──
        gr    = self.goal.move(-cx, -cy)
        blink = (tick // 350) % 2
        gc    = (255, 215, 40) if blink else (170, 140, 15)
        pygame.draw.rect(screen, (55, 38, 15), gr, border_radius=4)
        pygame.draw.rect(screen, gc, gr, 3, border_radius=4)
        mid_gx = gr.x + gr.w // 2
        pygame.draw.line(screen, gc, (mid_gx, gr.y+4), (mid_gx, gr.bottom-4), 2)
        # 별 아이콘
        star_y = gr.y + gr.h // 2
        pygame.draw.circle(screen, gc, (mid_gx, star_y), 6)

    # ── 미니맵 ───────────────────────────────────────────
    def draw_minimap(self, screen, player_x, player_y, screen_w):

        mm_x, mm_y = screen_w - 215, 10
        mm_w, mm_h = 200, 38
        sx = mm_w / self.map_width
        sy = mm_h / self.map_height

        bg = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 130))
        screen.blit(bg, (mm_x, mm_y))

        for p in self.platforms:
            r = pygame.Rect(int(p.x*sx), int(p.y*sy),
                            max(int(p.w*sx),1), max(int(p.h*sy),1))
            pygame.draw.rect(screen, (110,122,138), r.move(mm_x, mm_y))

        for lv in self.lavas:
            r = pygame.Rect(int(lv.x*sx), int(lv.y*sy),
                            max(int(lv.w*sx),1), max(int(lv.h*sy),1))
            pygame.draw.rect(screen, (210,55,0), r.move(mm_x, mm_y))

        for laser in self.lasers:
            lr = laser.rect
            r  = pygame.Rect(int(lr.x*sx), int(lr.y*sy),
                             max(int(lr.w*sx),1), max(int(lr.h*sy),1))
            color = (0, 200, 255) if laser.active else (0, 60, 100)
            pygame.draw.rect(screen, color, r.move(mm_x, mm_y))

        gr = pygame.Rect(int(self.goal.x*sx), int(self.goal.y*sy),
                         max(int(self.goal.w*sx),3), max(int(self.goal.h*sy),3))
        pygame.draw.rect(screen, (255,210,40), gr.move(mm_x, mm_y))

        px = int(player_x * sx) + mm_x
        py = int(player_y * sy) + mm_y
        pygame.draw.circle(screen, (100, 220, 255), (px, py), 3)

        pygame.draw.rect(screen, (170,170,170), (mm_x, mm_y, mm_w, mm_h), 1)
