# scripts/screens.py
"""
타이틀 / 게임오버 / 스테이지클리어 / 전체클리어 화면
각 함수는 screen 에 직접 그리며 scaled_font 유틸을 받아 사용한다.
"""

import pygame, math, random

# ── 파티클 풀 (모든 화면 공유) ───────────────────────────
_particles = []   # [(x, y, vx, vy, life, max_life, color, size)]


def _spawn_particles(cx, cy, n, colors, speed=2.0, spread=math.pi*2):
    for _ in range(n):
        a  = random.uniform(0, spread)
        sp = random.uniform(0.3, speed)
        life = random.randint(30, 80)
        col  = random.choice(colors)
        _particles.append([
            cx + random.randint(-20, 20),
            cy + random.randint(-20, 20),
            math.cos(a) * sp,
            math.sin(a) * sp,
            life, life,
            col,
            random.randint(2, 5)
        ])


def _update_draw_particles(screen):
    global _particles
    alive = []
    for p in _particles:
        p[0] += p[2]; p[1] += p[3]
        p[3] += 0.04          # 중력
        p[4] -= 1
        if p[4] > 0:
            a = int(255 * p[4] / p[5])
            s = pygame.Surface((p[7]*2, p[7]*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p[6], a), (p[7], p[7]), p[7])
            screen.blit(s, (int(p[0])-p[7], int(p[1])-p[7]))
            alive.append(p)
    _particles[:] = alive


def _draw_stars(screen, tick, sw, sh, star_list):
    """배경 별빛 반짝임"""
    for sx, sy, br, sr in star_list:
        a = int(180 * br * abs(math.sin(tick * 0.018 + br * 3)))
        c = (200 + int(br*30), 190 + int(br*30), 255)
        s = pygame.Surface((sr*4, sr*4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*c, a), (sr*2, sr*2), sr)
        screen.blit(s, (sx - sr*2, sy - sr*2))


def _glow_text(screen, text, font, x, y, color, glow_col=None, glow_r=3):
    """텍스트에 발광 효과"""
    if glow_col is None:
        glow_col = tuple(min(255, c+80) for c in color)
    for dx in range(-glow_r, glow_r+1):
        for dy in range(-glow_r, glow_r+1):
            if dx*dx + dy*dy <= glow_r*glow_r:
                s = font.render(text, True, (*glow_col, 80))
                screen.blit(s, (x+dx, y+dy))
    screen.blit(font.render(text, True, color), (x, y))


# ══════════════════════════════════════════════════════════
#  타이틀 화면
# ══════════════════════════════════════════════════════════
_title_stars = [(random.randint(0,800), random.randint(0,600),
                 random.uniform(0.3,1.0), random.randint(1,3))
                for _ in range(100)]
_title_orbs  = [(random.randint(0,800), random.randint(0,600),
                 random.uniform(0.5,2.0)) for _ in range(8)]

def draw_title(screen, tick):
    sw, sh = screen.get_size()
    screen.fill((6, 4, 14))

    _draw_stars(screen, tick, sw, sh, _title_stars)

    # 배경 마법진
    for i in range(3):
        r  = 120 + i*50
        a2 = tick * (0.003 + i*0.002) * (1 if i%2==0 else -1)
        col = [(40,10,80),(20,10,60),(60,20,100)][i]
        surf = pygame.Surface((r*2+10, r*2+10), pygame.SRCALPHA)
        n = 6 + i*3
        pts = [(int(r+r*math.cos(2*math.pi/n*k+a2)),
                int(r+r*math.sin(2*math.pi/n*k+a2))) for k in range(n)]
        pygame.draw.polygon(surf, (*col, 60), pts, 2)
        screen.blit(surf, (sw//2 - r - 5, sh//2 - r - 5 + 30))

    # 떠다니는 오브
    for ox, oy, spd in _title_orbs:
        fx = ox + math.sin(tick*spd*0.02)*30
        fy = oy + math.cos(tick*spd*0.015)*20
        pulse = int(abs(math.sin(tick*spd*0.04))*40)
        s = pygame.Surface((28,28), pygame.SRCALPHA)
        pygame.draw.circle(s, (100, 50, 200, 60+pulse), (14,14), 12)
        pygame.draw.circle(s, (180,120,255,140+pulse),  (14,14), 6)
        screen.blit(s, (int(fx)-14, int(fy)-14))

    # 제목 "SOUL KNIGHT"
    font_t = pygame.font.SysFont(None, int(sh*0.16))
    ty     = int(sh * 0.28)
    pulse  = int(abs(math.sin(tick*0.04))*15)
    _glow_text(screen,
               "SOUL  KNIGHT",
               font_t,
               sw//2 - font_t.size("SOUL  KNIGHT")[0]//2,
               ty,
               (255, 210+pulse, 60),
               glow_col=(180, 80, 255),
               glow_r=4)

    # 부제
    font_s = pygame.font.SysFont(None, int(sh*0.05))
    sub    = font_s.render("Descend into the dungeon. Survive.", True, (160,140,200))
    screen.blit(sub, (sw//2 - sub.get_width()//2, ty + int(sh*0.13)))

    # 구분선
    lx = sw//2
    pygame.draw.line(screen, (100,60,180), (lx-160, ty+int(sh*0.185)),
                     (lx+160, ty+int(sh*0.185)), 1)

    # PRESS ENTER
    if (tick//30) % 2 == 0:
        font_p = pygame.font.SysFont(None, int(sh*0.055))
        pt     = font_p.render("PRESS  ENTER  TO  START", True, (200,180,255))
        screen.blit(pt, (sw//2 - pt.get_width()//2, int(sh*0.62)))

    # 조작 안내
    font_c = pygame.font.SysFont(None, int(sh*0.036))
    hints  = [
        "WASD: Move    LClick: Attack",
        "G: Settings    P: Cheat    ESC: Quit",
    ]
    for i, h in enumerate(hints):
        ht = font_c.render(h, True, (90,80,120))
        screen.blit(ht, (sw//2 - ht.get_width()//2, int(sh*0.78) + i*28))

    # 버전
    vt = pygame.font.SysFont(None, 18).render("v1.0  |  Soul Knight", True, (60,50,90))
    screen.blit(vt, (sw - vt.get_width() - 10, sh - 20))


# ══════════════════════════════════════════════════════════
#  게임 오버 화면
# ══════════════════════════════════════════════════════════
_go_particles_spawned = False
_go_tick_offset = 0

def draw_gameover(screen, gm, tick, scaled_font_fn):
    global _go_particles_spawned, _go_tick_offset
    sw, sh = screen.get_size()

    # 피처럼 번지는 배경
    t_ratio = min((tick - _go_tick_offset) / 60, 1.0)
    r_val   = int(10 + 30 * t_ratio)
    screen.fill((r_val, 2, 4))

    # 어두운 비네팅
    vign = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for ri in range(20, 0, -1):
        a = int((20-ri)*4)
        rw = int(sw*(ri/20)); rh = int(sh*(ri/20))
        pygame.draw.rect(vign, (0,0,0,a),
                         (sw//2-rw//2, sh//2-rh//2, rw, rh), 6)
    screen.blit(vign, (0,0))

    # 파티클 (한 번만 생성)
    if not _go_particles_spawned:
        _spawn_particles(sw//2, sh//3, 40,
                         [(200,30,30),(255,80,40),(180,10,10)],
                         speed=3.5)
        _go_particles_spawned = True
    _update_draw_particles(screen)

    # GAME OVER 텍스트
    font1 = scaled_font_fn(90)
    t1x   = sw//2 - font1.size("GAME  OVER")[0]//2
    t1y   = int(sh * 0.22)
    shake = int(math.sin(tick*0.3)*2)
    _glow_text(screen, "GAME  OVER", font1,
               t1x + shake, t1y,
               (230, 45, 45), glow_col=(120,10,10), glow_r=5)

    # 구분선
    pygame.draw.line(screen, (180,30,30),
                     (sw//2-200, t1y+80), (sw//2+200, t1y+80), 2)

    # 스탯
    font2 = scaled_font_fn(32)
    font3 = scaled_font_fn(24)
    stats = [
        (f"Stage Reached :  {gm.stage}", (200,160,160)),
        (f"Score  :  {gm.score}",        (200,180,140)),
        (f"Coins  :  {gm.coins}",        (220,200,100)),
    ]
    for i, (txt, col) in enumerate(stats):
        t = font2.render(txt, True, col)
        screen.blit(t, (sw//2 - t.get_width()//2, t1y + 110 + i*44))

    # 안내
    if (tick//25) % 2 == 0:
        pt = font3.render("Press  R  to return to Lobby", True, (160,120,120))
        screen.blit(pt, (sw//2 - pt.get_width()//2, int(sh*0.75)))

def reset_gameover():
    global _go_particles_spawned, _go_tick_offset
    _go_particles_spawned = False


# ══════════════════════════════════════════════════════════
#  스테이지 클리어 화면
# ══════════════════════════════════════════════════════════
_cl_confetti = []
_cl_spawned  = False

def _spawn_confetti(sw, sh):
    global _cl_confetti
    cols = [(255,220,60),(100,255,160),(80,160,255),(255,100,200),(200,255,80)]
    _cl_confetti = [
        [random.randint(0,sw), random.randint(-sh,0),
         random.uniform(-1.5,1.5), random.uniform(1,3),
         random.choice(cols), random.randint(4,9),
         random.uniform(0,math.pi*2)]
        for _ in range(120)
    ]

def draw_clear(screen, gm, tick, scaled_font_fn):
    global _cl_spawned, _cl_confetti
    sw, sh = screen.get_size()
    screen.fill((4, 16, 10))

    # 빛 방사
    for i in range(5):
        a2  = tick * 0.01 + i * math.pi*2/5
        r2  = int(sh * 0.35)
        ex  = sw//2 + int(math.cos(a2)*20)
        ey  = int(sh*0.35)
        for ri in range(3):
            s = pygame.Surface((r2*2, r2*2), pygame.SRCALPHA)
            alpha = [30,18,8][ri]
            pygame.draw.circle(s, (80,220,120,alpha), (r2,r2), r2-ri*20)
            screen.blit(s, (ex-r2, ey-r2))

    # 색종이 생성 (1회)
    if not _cl_spawned:
        _spawn_confetti(sw, sh)
        _cl_spawned = True

    # 색종이 업데이트·그리기
    for c in _cl_confetti:
        c[0] += c[2]; c[1] += c[3]; c[6] += 0.08
        if c[1] > sh: c[1] = -10; c[0] = random.randint(0,sw)
        sz = c[5]
        pts = [
            (int(c[0] + sz*math.cos(c[6])),
             int(c[1] + sz*math.sin(c[6]))),
            (int(c[0] + sz*math.cos(c[6]+2.1)),
             int(c[1] + sz*math.sin(c[6]+2.1))),
            (int(c[0] + sz*math.cos(c[6]+4.2)),
             int(c[1] + sz*math.sin(c[6]+4.2))),
        ]
        pygame.draw.polygon(screen, c[4], pts)

    # STAGE CLEAR 텍스트
    font1 = scaled_font_fn(88)
    t1x   = sw//2 - font1.size("STAGE  CLEAR!")[0]//2
    t1y   = int(sh * 0.20)
    pulse = int(abs(math.sin(tick*0.06))*20)
    _glow_text(screen, "STAGE  CLEAR!", font1, t1x, t1y,
               (100+pulse, 255, 160), glow_col=(20,160,80), glow_r=4)

    # 스테이지 번호
    font_st = scaled_font_fn(36)
    st_txt  = font_st.render(f"─  Floor {gm.stage}  Cleared  ─", True, (160,240,190))
    screen.blit(st_txt, (sw//2 - st_txt.get_width()//2, t1y + 90))

    # 구분선
    pygame.draw.line(screen, (60,200,110),
                     (sw//2-220, t1y+128), (sw//2+220, t1y+128), 1)

    # 스탯
    font2 = scaled_font_fn(30)
    font3 = scaled_font_fn(24)
    stats = [
        (f"Score  :  {gm.score}",             (220,255,200)),
        (f"Coins  :  {gm.coins}",             (255,230,80)),
        (f"Reroll Tickets  :  {gm.reroll_tickets}", (180,160,255)),
    ]
    for i, (txt, col) in enumerate(stats):
        t = font2.render(txt, True, col)
        screen.blit(t, (sw//2 - t.get_width()//2, t1y + 148 + i*42))

    # 안내
    if (tick//28) % 2 == 0:
        next_txt = "Press  SPACE  to next Floor" if gm.stage < 5 else "Press  SPACE  to Final Clear"
        pt = font3.render(next_txt, True, (120,200,140))
        screen.blit(pt, (sw//2 - pt.get_width()//2, int(sh*0.78)))

def reset_clear():
    global _cl_spawned, _cl_confetti
    _cl_spawned  = False
    _cl_confetti = []


# ══════════════════════════════════════════════════════════
#  전체 클리어 (파이널) 화면
# ══════════════════════════════════════════════════════════
_fc_spawned = False
_fc_stars2  = [(random.randint(0,800), random.randint(0,600),
                random.uniform(0.3,1.0), random.randint(1,4))
               for _ in range(150)]

def draw_final_clear(screen, gm, tick, scaled_font_fn):
    global _fc_spawned
    sw, sh = screen.get_size()
    screen.fill((4, 4, 20))

    _draw_stars(screen, tick, sw, sh, _fc_stars2)

    # 무지개 광환
    for i in range(8):
        a3   = tick * 0.008 + i * math.pi*2/8
        r3   = int(sh*0.38) + int(math.sin(tick*0.04+i)*15)
        col3 = pygame.Color(0); col3.hsva = (i/8*360, 80, 90, 100)
        s3   = pygame.Surface((r3*2+6, r3*2+6), pygame.SRCALPHA)
        pygame.draw.circle(s3, (*col3[:3], 35), (r3+3, r3+3), r3, 4)
        screen.blit(s3, (sw//2-r3-3, sh//2-r3-3-40))

    # 파티클 (1회)
    if not _fc_spawned:
        _spawn_particles(sw//2, sh//2, 80,
                         [(255,220,60),(255,150,50),(200,100,255),
                          (80,220,255),(100,255,160)],
                         speed=4.0)
        _fc_spawned = True
    _update_draw_particles(screen)

    # ALL STAGES CLEAR!
    font1 = scaled_font_fn(80)
    txt1  = "ALL STAGES  CLEAR!"
    t1x   = sw//2 - font1.size(txt1)[0]//2
    t1y   = int(sh * 0.18)
    hue   = (tick * 2) % 360
    rc    = pygame.Color(0); rc.hsva = (hue, 90, 100, 100)
    _glow_text(screen, txt1, font1, t1x, t1y,
               rc[:3], glow_col=(180,100,255), glow_r=5)

    # 부제
    font_s2 = scaled_font_fn(36)
    sub2    = font_s2.render("You conquered all 5 floors!", True, (220,200,255))
    screen.blit(sub2, (sw//2 - sub2.get_width()//2, t1y + 96))

    # 구분선
    pygame.draw.line(screen, (180,140,255),
                     (sw//2-240, t1y+135), (sw//2+240, t1y+135), 1)

    # 최종 스탯
    font2 = scaled_font_fn(30)
    font3 = scaled_font_fn(24)
    stats = [
        (f"Final Score  :  {gm.score}",  (255,240,100)),
        (f"Coins Earned :  {gm.coins}",  (255,220,60)),
    ]
    for i, (txt, col) in enumerate(stats):
        t = font2.render(txt, True, col)
        screen.blit(t, (sw//2 - t.get_width()//2, t1y + 158 + i*44))

    # 감사 메시지
    thx = scaled_font_fn(26).render("Thank you for playing!", True, (180,160,220))
    screen.blit(thx, (sw//2 - thx.get_width()//2, t1y + 268))

    # 안내
    if (tick//30) % 2 == 0:
        pt = font3.render("Press  R  to start over", True, (140,120,180))
        screen.blit(pt, (sw//2 - pt.get_width()//2, int(sh*0.82)))

def reset_final_clear():
    global _fc_spawned
    _fc_spawned = False
