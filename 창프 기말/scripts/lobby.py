# scripts/lobby.py
"""
소울나이트 로비 — 주사위 스탯 업그레이드 시스템
- 로비 진입 시 자동으로 주사위 1세트 롤
- 리롤권 1개 소비 → 재롤 (결과 다시 뽑기)
- 코인 30개 → 리롤권 1개 구매 (고정 가격)
- 보스 처치 시 리롤권 1개 드롭
- ENTER STAGE 클릭 → 현재 롤 결과를 플레이어에 적용 후 입장
"""

import pygame, math, random, sys
sys.path.insert(0, '.')
from scripts import player_base

DRAW_SIZE        = 80
TICKET_BUY_COST  = 30   # 리롤권 1개 구매 비용 (고정)

# ── 스탯 롤 정의 ──────────────────────────────────────────
# (key, 표시명, 배율, 단위 문자열, 색상)
STAT_DEFS = [
    ("hp",   "HP",    5,    "+{v}",   (220,  80,  80)),
    ("spd",  "SPD",   0.05, "+{v:.2f}",(80, 220, 100)),
    ("atk",  "ATK",   1,    "+{v}",   (255, 200,  60)),
    ("cd",   "CD",    1,    "-{v}tick",(80, 160, 255)),
]

# ── 색상 팔레트 ────────────────────────────────────────────
C_BG       = (12,  10,  22)
C_PANEL    = (22,  18,  40)
C_PANEL2   = (30,  24,  55)
C_BORDER   = (80,  60, 140)
C_GOLD     = (255, 210,  60)
C_WHITE    = (230, 230, 230)
C_GRAY     = (140, 130, 160)
C_GREEN    = ( 80, 220, 100)
C_RED      = (220,  60,  60)
C_BLUE     = ( 80, 160, 255)
C_BTN      = ( 50,  40,  90)
C_BTN_HOV  = ( 70,  55, 120)
C_START    = ( 40, 120,  60)
C_START_H  = ( 60, 160,  80)
C_REROLL   = ( 90,  50,  20)
C_REROLL_H = (130,  75,  30)
C_BUY      = ( 20,  60,  90)
C_BUY_H    = ( 30,  90, 130)
C_LOCKED   = ( 40,  35,  55)


def _load_idle_frames():
    return [
        pygame.transform.scale(f.copy(), (DRAW_SIZE, DRAW_SIZE))
        for f in player_base.IDLE_0
    ]


class Button:
    def __init__(self, x, y, w, h, text, color=C_BTN, hover=C_BTN_HOV):
        self.rect  = pygame.Rect(x, y, w, h)
        self.text  = text
        self.color = color
        self.hover = hover
        self._font = None

    def draw(self, screen, disabled=False):
        if self._font is None:
            self._font = pygame.font.SysFont(None, 26)
        col = C_LOCKED if disabled else (
            self.hover if self.rect.collidepoint(pygame.mouse.get_pos()) else self.color
        )
        pygame.draw.rect(screen, col, self.rect, border_radius=6)
        pygame.draw.rect(screen, C_BORDER if not disabled else (50, 45, 65),
                         self.rect, 2, border_radius=6)
        tc = C_GRAY if disabled else C_WHITE
        t = self._font.render(self.text, True, tc)
        screen.blit(t, (self.rect.centerx - t.get_width()//2,
                        self.rect.centery - t.get_height()//2))

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))


def _dice_face(surface, x, y, size, value, color):
    """주사위 면 그리기 (1~6 점 배치)"""
    s = size
    pygame.draw.rect(surface, (30, 22, 50), (x, y, s, s), border_radius=8)
    pygame.draw.rect(surface, color,        (x, y, s, s), 2, border_radius=8)

    dot_r = max(3, s // 10)
    pad   = s // 5
    cx, cy = x + s//2, y + s//2

    positions = {
        1: [(cx, cy)],
        2: [(x+pad, y+pad), (x+s-pad, y+s-pad)],
        3: [(x+pad, y+pad), (cx, cy), (x+s-pad, y+s-pad)],
        4: [(x+pad, y+pad), (x+s-pad, y+pad),
            (x+pad, y+s-pad), (x+s-pad, y+s-pad)],
        5: [(x+pad, y+pad), (x+s-pad, y+pad), (cx, cy),
            (x+pad, y+s-pad), (x+s-pad, y+s-pad)],
        6: [(x+pad, y+pad), (x+s-pad, y+pad),
            (x+pad, cy),     (x+s-pad, cy),
            (x+pad, y+s-pad),(x+s-pad, y+s-pad)],
    }
    for px, py in positions.get(value, []):
        pygame.draw.circle(surface, color, (px, py), dot_r)


class Lobby:
    def __init__(self, player):
        self.player  = player
        self._frames = None
        self._anim_i = 0
        self._anim_t = 0
        self._tick   = 0

        # 현재 롤 결과 {key: dice_value(1~6)}
        self._roll: dict = {}
        self._roll_generated = False   # 이번 로비 방문에서 이미 롤했는지

        # 버튼
        self.btn_reroll = Button(0, 0, 180, 38, "REROLL  (1 ticket)",
                                 color=C_REROLL, hover=C_REROLL_H)
        self.btn_buy    = Button(0, 0, 180, 38,
                                 f"BUY TICKET  ({TICKET_BUY_COST}c)",
                                 color=C_BUY, hover=C_BUY_H)
        self.btn_start  = Button(0, 0, 240, 50, "ENTER STAGE",
                                 color=C_START, hover=C_START_H)

        import random as _r
        self._stars = [
            (_r.randint(0, 800), _r.randint(0, 600),
             _r.uniform(0.2, 1.0), _r.randint(1, 3))
            for _ in range(80)
        ]

    # ── 내부 ─────────────────────────────────────────────

    def _ensure_frames(self):
        if self._frames is None:
            self._frames = _load_idle_frames()

    def _new_roll(self):
        """주사위 4개(HP/SPD/ATK/CD) 1~6 랜덤 롤"""
        self._roll = {key: random.randint(1, 6) for key, *_ in STAT_DEFS}

    def _apply_roll(self):
        """현재 롤 결과를 플레이어 스탯에 영구 적용"""
        p = self.player
        for key, _, scale, *_ in STAT_DEFS:
            v = self._roll.get(key, 0)
            if key == "hp":
                p.max_hp += v * int(scale)
                p.hp      = p.max_hp
            elif key == "spd":
                p.speed  = round(p.speed + v * scale, 3)
            elif key == "atk":
                p.damage += v * int(scale)
            elif key == "cd":
                p.fire_rate = max(8, p.fire_rate - v * int(scale))

    def on_enter_lobby(self):
        """로비에 들어올 때마다 새 롤 자동 생성"""
        self._new_roll()
        self._roll_generated = True

    # ── 이벤트 ───────────────────────────────────────────

    def handle_event(self, event, gm):
        # 아직 롤이 없으면 자동 생성
        if not self._roll_generated:
            self.on_enter_lobby()

        if self.btn_start.is_clicked(event):
            self._apply_roll()
            self._roll_generated = False   # 다음 로비 방문 시 새 롤
            gm.state = "STAGE1"
            return

        if self.btn_reroll.is_clicked(event):
            if gm.reroll_tickets > 0:
                gm.reroll_tickets -= 1
                self._new_roll()

        if self.btn_buy.is_clicked(event):
            if gm.coins >= TICKET_BUY_COST:
                gm.coins -= TICKET_BUY_COST
                gm.reroll_tickets += 1

    # ── 업데이트 ─────────────────────────────────────────

    def update(self, keys):
        self._ensure_frames()
        if not self._roll_generated:
            self.on_enter_lobby()
        self._tick += 1
        self._anim_t += 1
        if self._anim_t >= 10:
            self._anim_t = 0
            self._anim_i = (self._anim_i + 1) % len(self._frames)

    # ── 그리기 ───────────────────────────────────────────

    def draw(self, screen, gm):
        sw, sh = screen.get_size()
        screen.fill(C_BG)

        # 별
        for sx, sy, br, sr in self._stars:
            pygame.draw.circle(screen, (200, 190, 255), (sx, sy), sr)

        # ── 제목 ──
        font_title = pygame.font.SysFont(None, 62)
        t = font_title.render("SOUL  KNIGHT", True, C_GOLD)
        screen.blit(t, (sw//2 - t.get_width()//2, 22))
        font_sub = pygame.font.SysFont(None, 26)
        sub = font_sub.render("Roll the dice. Choose your fate.", True, C_GRAY)
        screen.blit(sub, (sw//2 - sub.get_width()//2, 82))

        # ── 캐릭터 패널 (좌측) ──────────────────────────
        char_rect = pygame.Rect(30, 110, 210, 360)
        pygame.draw.rect(screen, C_PANEL, char_rect, border_radius=12)
        pygame.draw.rect(screen, C_BORDER, char_rect, 2, border_radius=12)

        if self._frames:
            img = self._frames[self._anim_i]
            float_y = int(math.sin(self._tick * 0.06) * 5)
            ix = char_rect.centerx - DRAW_SIZE//2
            iy = char_rect.top + 20 + float_y
            shadow = pygame.Surface((60, 16), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 80), (0, 0, 60, 16))
            screen.blit(shadow, (ix + 10, iy + DRAW_SIZE - 6))
            screen.blit(img, (ix, iy))

        font_name = pygame.font.SysFont(None, 28)
        nm = font_name.render("The Wanderer", True, C_GOLD)
        screen.blit(nm, (char_rect.centerx - nm.get_width()//2,
                         char_rect.top + 118))

        p = self.player
        font_stat = pygame.font.SysFont(None, 22)
        stats_display = [
            ("HP",   f"{p.hp}/{p.max_hp}", C_RED),
            ("SPD",  f"{p.speed:.2f}",     C_GREEN),
            ("ATK",  f"{p.damage}",         C_GOLD),
            ("CD",   f"{p.fire_rate}tk",   C_BLUE),
        ]
        sy0 = char_rect.top + 150
        for i, (lbl, val, col) in enumerate(stats_display):
            yl = sy0 + i * 36
            pygame.draw.rect(screen, C_PANEL2,
                             (char_rect.left+12, yl, char_rect.width-24, 28),
                             border_radius=4)
            lt = font_stat.render(lbl, True, C_GRAY)
            vt = font_stat.render(val, True, col)
            screen.blit(lt, (char_rect.left + 20, yl + 6))
            screen.blit(vt, (char_rect.right - vt.get_width() - 16, yl + 6))

        # ── 주사위 패널 (중앙) ──────────────────────────
        dice_rect = pygame.Rect(260, 110, 320, 360)
        pygame.draw.rect(screen, C_PANEL, dice_rect, border_radius=12)
        pygame.draw.rect(screen, C_BORDER, dice_rect, 2, border_radius=12)

        font_dt = pygame.font.SysFont(None, 30)
        dt_txt = font_dt.render("THIS RUN'S BONUS", True, C_GOLD)
        screen.blit(dt_txt, (dice_rect.centerx - dt_txt.get_width()//2,
                              dice_rect.top + 12))

        dice_size = 54
        row_h     = 72
        dy0       = dice_rect.top + 52
        font_dl   = pygame.font.SysFont(None, 22)

        for i, (key, name, scale, fmt, col) in enumerate(STAT_DEFS):
            dv  = self._roll.get(key, 1)
            row_y = dy0 + i * row_h

            # 스탯 이름
            lt = font_dl.render(name, True, col)
            screen.blit(lt, (dice_rect.left + 16, row_y + (dice_size - lt.get_height())//2))

            # 주사위 그림
            dx = dice_rect.left + 68
            _dice_face(screen, dx, row_y, dice_size, dv, col)

            # 보너스 수치
            actual = dv * scale
            if key == "cd":
                bonus_str = fmt.format(v=int(actual))
            elif key == "spd":
                bonus_str = fmt.format(v=actual)
            else:
                bonus_str = fmt.format(v=int(actual))
            bt = font_dl.render(bonus_str, True, col)
            screen.blit(bt, (dx + dice_size + 14,
                              row_y + (dice_size - bt.get_height())//2))

        # ── 리롤/구매 패널 (우측) ──────────────────────
        side_rect = pygame.Rect(600, 110, 170, 360)
        pygame.draw.rect(screen, C_PANEL, side_rect, border_radius=12)
        pygame.draw.rect(screen, C_BORDER, side_rect, 2, border_radius=12)

        font_s = pygame.font.SysFont(None, 26)

        # 리롤권 수
        tk_txt = font_s.render("TICKETS", True, C_GOLD)
        screen.blit(tk_txt, (side_rect.centerx - tk_txt.get_width()//2,
                              side_rect.top + 12))
        font_big = pygame.font.SysFont(None, 64)
        nt = font_big.render(str(gm.reroll_tickets), True, C_WHITE)
        screen.blit(nt, (side_rect.centerx - nt.get_width()//2,
                         side_rect.top + 38))

        # 코인
        font_coin = pygame.font.SysFont(None, 24)
        ct = font_coin.render(f"Coins: {gm.coins}", True, C_GOLD)
        screen.blit(ct, (side_rect.centerx - ct.get_width()//2,
                         side_rect.top + 102))

        # REROLL 버튼
        self.btn_reroll.rect.centerx = side_rect.centerx
        self.btn_reroll.rect.y       = side_rect.top + 138
        self.btn_reroll.rect.width   = side_rect.width - 16
        no_ticket = gm.reroll_tickets <= 0
        self.btn_reroll.draw(screen, disabled=no_ticket)
        hint1 = font_coin.render("(use 1 ticket)", True, C_GRAY)
        screen.blit(hint1, (side_rect.centerx - hint1.get_width()//2,
                             self.btn_reroll.rect.bottom + 3))

        # BUY TICKET 버튼
        self.btn_buy.rect.centerx = side_rect.centerx
        self.btn_buy.rect.y       = side_rect.top + 215
        self.btn_buy.rect.width   = side_rect.width - 16
        cant_buy = gm.coins < TICKET_BUY_COST
        self.btn_buy.draw(screen, disabled=cant_buy)
        hint2 = font_coin.render(f"({TICKET_BUY_COST} coins each)", True, C_GRAY)
        screen.blit(hint2, (side_rect.centerx - hint2.get_width()//2,
                             self.btn_buy.rect.bottom + 3))

        # 획득처 안내
        font_hint = pygame.font.SysFont(None, 20)
        tip = font_hint.render("Boss drop: +1 ticket", True, (160, 100, 220))
        screen.blit(tip, (side_rect.centerx - tip.get_width()//2,
                          side_rect.bottom - 28))

        # ── 입장 버튼 ──
        self.btn_start.rect.centerx = sw // 2
        self.btn_start.rect.y       = sh - 72
        self.btn_start.draw(screen)

        # 조작 안내
        font_ctrl = pygame.font.SysFont(None, 20)
        ctrl = font_ctrl.render(
            "WASD: Move    LClick: Attack    ESC: Quit", True, C_GRAY)
        screen.blit(ctrl, (sw//2 - ctrl.get_width()//2, sh - 24))
