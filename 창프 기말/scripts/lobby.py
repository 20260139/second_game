# scripts/lobby.py

import pygame, math, random, sys
sys.path.insert(0, '.')
from scripts import player_base

DRAW_SIZE       = 80
TICKET_BUY_COST = 30

# 플레이어 기본 스탯 (로비 복귀 시 이 값으로 초기화)
BASE_STATS = {
    "max_hp"   : 100,
    "hp"       : 100,
    "speed"    : 3.2,
    "damage"   : 20,
    "fire_rate": 22,
}

# ── 스탯 배율 정의 ──────────────────────────────────────
# (key, 표시명, 배율, 포맷, 색상)
STAT_DEFS = [
    ("hp",  "HP",   10,   "+{v} HP",    (220,  80,  80)),
    ("spd", "SPD",  0.10, "+{v:.1f} SPD",(80, 220, 100)),
    ("atk", "ATK",  3,    "+{v} ATK",   (255, 200,  60)),
    ("cd",  "CD",   2,    "-{v} tick",  ( 80, 160, 255)),
]

# ── 주사위 굴림 애니메이션 길이(틱) ──────────────────────
ROLL_ANIM_TICKS = 18   # 이 틱 동안 빠르게 숫자가 바뀌다 확정

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


def _dice_face(surface, x, y, size, value, color, rolling=False):
    """주사위 면 그리기. rolling=True 이면 테두리를 밝게."""
    border_col = (255, 255, 180) if rolling else color
    pygame.draw.rect(surface, (30, 22, 50), (x, y, size, size), border_radius=8)
    pygame.draw.rect(surface, border_col,   (x, y, size, size),
                     3 if rolling else 2, border_radius=8)

    dot_r = max(3, size // 10)
    pad   = size // 5
    cx, cy = x + size//2, y + size//2

    positions = {
        1: [(cx, cy)],
        2: [(x+pad, y+pad), (x+size-pad, y+size-pad)],
        3: [(x+pad, y+pad), (cx, cy), (x+size-pad, y+size-pad)],
        4: [(x+pad, y+pad), (x+size-pad, y+pad),
            (x+pad, y+size-pad), (x+size-pad, y+size-pad)],
        5: [(x+pad, y+pad), (x+size-pad, y+pad), (cx, cy),
            (x+pad, y+size-pad), (x+size-pad, y+size-pad)],
        6: [(x+pad, y+pad), (x+size-pad, y+pad),
            (x+pad, cy),     (x+size-pad, cy),
            (x+pad, y+size-pad), (x+size-pad, y+size-pad)],
    }
    dot_col = (255, 255, 180) if rolling else color
    for px, py in positions.get(max(1, min(6, value)), []):
        pygame.draw.circle(surface, dot_col, (px, py), dot_r)


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


class Lobby:
    def __init__(self, player):
        self.player  = player
        self._frames = None
        self._anim_i = 0
        self._anim_t = 0
        self._tick   = 0

        # 확정된 롤 결과 {key: 1~6}
        self._roll: dict = {}
        self._roll_generated = False

        # 주사위 개별 굴림 애니메이션
        # {key: 남은 틱} — 0이면 정지, 양수면 굴림 중
        self._rolling: dict = {key: 0 for key, *_ in STAT_DEFS}
        # 굴림 중 임시 표시 값 (매 틱 랜덤)
        self._roll_show: dict = {}

        # 주사위 클릭 영역 (draw에서 갱신) {key: pygame.Rect}
        self._dice_rects: dict = {}

        # 버튼
        self.btn_reroll = Button(0, 0, 180, 38, "REROLL ALL (1 ticket)",
                                 color=C_REROLL, hover=C_REROLL_H)
        self.btn_buy    = Button(0, 0, 180, 38,
                                 f"BUY TICKET  ({TICKET_BUY_COST}c)",
                                 color=C_BUY, hover=C_BUY_H)
        self.btn_start  = Button(0, 0, 240, 50, "ENTER STAGE",
                                 color=C_START, hover=C_START_H)

        self._stars = [
            (random.randint(0, 800), random.randint(0, 600),
             random.uniform(0.2, 1.0), random.randint(1, 3))
            for _ in range(80)
        ]

    # ── 내부 ─────────────────────────────────────────────

    def _ensure_frames(self):
        if self._frames is None:
            self._frames = _load_idle_frames()

    def _new_roll(self, keys=None):
        """keys 가 None 이면 전체, 아니면 지정 key만 새로 롤."""
        targets = keys if keys else [k for k, *_ in STAT_DEFS]
        for key in targets:
            self._roll[key] = random.randint(1, 6)

    def _start_rolling_anim(self, keys=None):
        """지정 주사위(또는 전체)의 굴림 애니메이션 시작."""
        targets = keys if keys else [k for k, *_ in STAT_DEFS]
        for key in targets:
            self._rolling[key]   = ROLL_ANIM_TICKS
            self._roll_show[key] = random.randint(1, 6)

    def _apply_roll(self):
        """현재 롤 결과를 플레이어 스탯에 영구 적용."""
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
        """로비 진입 시: 스탯 초기화 + 자동 롤."""
        # 기본 스탯으로 완전 초기화 (로그라이크 방식 - 판마다 새로 시작)
        p = self.player
        p.max_hp    = BASE_STATS["max_hp"]
        p.hp        = BASE_STATS["hp"]
        p.speed     = BASE_STATS["speed"]
        p.damage    = BASE_STATS["damage"]
        p.fire_rate = BASE_STATS["fire_rate"]
        self._new_roll()
        self._start_rolling_anim()
        self._roll_generated = True

    # ── 이벤트 ───────────────────────────────────────────

    def handle_event(self, event, gm):
        if not self._roll_generated:
            self.on_enter_lobby()

        if self.btn_start.is_clicked(event):
            # 굴림 중인 주사위가 있으면 즉시 확정
            for key in list(self._rolling):
                self._rolling[key] = 0
            self._apply_roll()
            self._roll_generated = False
            gm.state = "STAGE1"
            return

        # 전체 리롤 버튼 (티켓 1개)
        if self.btn_reroll.is_clicked(event):
            if gm.reroll_tickets > 0:
                gm.reroll_tickets -= 1
                self._new_roll()
                self._start_rolling_anim()

        # 티켓 구매
        if self.btn_buy.is_clicked(event):
            if gm.coins >= TICKET_BUY_COST:
                gm.coins -= TICKET_BUY_COST
                gm.reroll_tickets += 1

        # ── 주사위 개별 클릭 → 티켓 1개 소모 후 해당 주사위만 재롤 ──
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and gm.reroll_tickets > 0):
            for key, dice_rect in self._dice_rects.items():
                if dice_rect.collidepoint(event.pos):
                    # 버튼과 중복 처리 방지 (버튼 영역 제외)
                    if (not self.btn_reroll.rect.collidepoint(event.pos) and
                            not self.btn_buy.rect.collidepoint(event.pos) and
                            not self.btn_start.rect.collidepoint(event.pos)):
                        gm.reroll_tickets -= 1
                        self._new_roll(keys=[key])
                        self._start_rolling_anim(keys=[key])
                        break

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

        # 주사위 굴림 애니메이션 틱 감소
        for key in list(self._rolling):
            if self._rolling[key] > 0:
                self._rolling[key] -= 1
                self._roll_show[key] = random.randint(1, 6)

    # ── 그리기 ───────────────────────────────────────────

    def draw(self, screen, gm):
        sw, sh = screen.get_size()
        screen.fill(C_BG)

        for sx, sy, br, sr in self._stars:
            pygame.draw.circle(screen, (200, 190, 255), (sx, sy), sr)

        # 제목
        font_title = pygame.font.SysFont(None, 62)
        t = font_title.render("SOUL  KNIGHT", True, C_GOLD)
        screen.blit(t, (sw//2 - t.get_width()//2, 22))
        font_sub = pygame.font.SysFont(None, 26)
        sub = font_sub.render("Click a die to reroll it  |  Roll the dice. Choose your fate.", True, C_GRAY)
        screen.blit(sub, (sw//2 - sub.get_width()//2, 80))

        # ── 캐릭터 패널 (좌측) ──────────────────────────
        char_rect = pygame.Rect(30, 108, 210, 360)
        pygame.draw.rect(screen, C_PANEL, char_rect, border_radius=12)
        pygame.draw.rect(screen, C_BORDER, char_rect, 2, border_radius=12)

        if self._frames:
            img = self._frames[self._anim_i]
            fy  = int(math.sin(self._tick * 0.06) * 5)
            ix  = char_rect.centerx - DRAW_SIZE//2
            iy  = char_rect.top + 18 + fy
            shadow = pygame.Surface((60, 16), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 80), (0, 0, 60, 16))
            screen.blit(shadow, (ix + 10, iy + DRAW_SIZE - 6))
            screen.blit(img, (ix, iy))

        font_name = pygame.font.SysFont(None, 28)
        nm = font_name.render("The Wanderer", True, C_GOLD)
        screen.blit(nm, (char_rect.centerx - nm.get_width()//2,
                         char_rect.top + 115))

        p = self.player
        font_stat = pygame.font.SysFont(None, 22)
        stats_display = [
            ("HP",  f"{p.hp}/{p.max_hp}", C_RED),
            ("SPD", f"{p.speed:.2f}",     C_GREEN),
            ("ATK", f"{p.damage}",         C_GOLD),
            ("CD",  f"{p.fire_rate}tk",   C_BLUE),
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
            screen.blit(vt, (char_rect.right - vt.get_width() - 14, yl + 6))

        # ── 주사위 패널 (중앙) ──────────────────────────
        dice_rect = pygame.Rect(258, 108, 330, 360)
        pygame.draw.rect(screen, C_PANEL, dice_rect, border_radius=12)
        pygame.draw.rect(screen, C_BORDER, dice_rect, 2, border_radius=12)

        font_dt = pygame.font.SysFont(None, 28)
        dt_txt = font_dt.render("THIS RUN'S BONUS", True, C_GOLD)
        screen.blit(dt_txt, (dice_rect.centerx - dt_txt.get_width()//2,
                              dice_rect.top + 10))

        # 클릭 안내 (티켓이 있을 때만)
        font_hint2 = pygame.font.SysFont(None, 19)
        if gm.reroll_tickets > 0:
            ht = font_hint2.render("(click a die = 1 ticket)", True, C_GOLD)
        else:
            ht = font_hint2.render("(no tickets — buy or earn from boss)", True, C_GRAY)
        screen.blit(ht, (dice_rect.centerx - ht.get_width()//2,
                         dice_rect.top + 34))

        dice_size = 56
        row_h     = 74
        dy0       = dice_rect.top + 58
        font_dl   = pygame.font.SysFont(None, 22)
        self._dice_rects = {}

        for i, (key, name, scale, fmt, col) in enumerate(STAT_DEFS):
            row_y   = dy0 + i * row_h
            rolling = self._rolling.get(key, 0) > 0

            # 굴림 중이면 임시 값, 아니면 확정 값
            dv = self._roll_show.get(key, 1) if rolling else self._roll.get(key, 1)

            # 스탯 이름
            lt = font_dl.render(name, True, col)
            screen.blit(lt, (dice_rect.left + 14,
                              row_y + (dice_size - lt.get_height())//2))

            # 주사위 (클릭 영역 저장)
            dx = dice_rect.left + 70
            dice_area = pygame.Rect(dx, row_y, dice_size, dice_size)
            self._dice_rects[key] = dice_area

            # 호버 강조 (티켓 있을 때만)
            hovered = (dice_area.collidepoint(pygame.mouse.get_pos())
                       and gm.reroll_tickets > 0)
            _dice_face(screen, dx, row_y, dice_size, dv, col,
                       rolling=rolling or hovered)

            # 커서 힌트
            if hovered and not rolling:
                font_tiny = pygame.font.SysFont(None, 17)
                ht2 = font_tiny.render("click!", True, (255, 255, 180))
                screen.blit(ht2, (dx, row_y - 14))

            # 보너스 수치
            actual = dv * scale
            if key in ("hp", "atk", "cd"):
                bonus_str = fmt.format(v=int(actual))
            else:
                bonus_str = fmt.format(v=actual)
            bt = font_dl.render(bonus_str, True,
                                 (200, 200, 200) if rolling else col)
            screen.blit(bt, (dx + dice_size + 12,
                              row_y + (dice_size - bt.get_height())//2))

        # ── 우측 패널 (티켓/구매) ──────────────────────
        side_rect = pygame.Rect(606, 108, 166, 360)
        pygame.draw.rect(screen, C_PANEL, side_rect, border_radius=12)
        pygame.draw.rect(screen, C_BORDER, side_rect, 2, border_radius=12)

        font_s    = pygame.font.SysFont(None, 26)
        font_coin = pygame.font.SysFont(None, 24)
        font_hint = pygame.font.SysFont(None, 19)

        tk_txt = font_s.render("TICKETS", True, C_GOLD)
        screen.blit(tk_txt, (side_rect.centerx - tk_txt.get_width()//2,
                              side_rect.top + 10))
        font_big = pygame.font.SysFont(None, 72)
        nt = font_big.render(str(gm.reroll_tickets), True, C_WHITE)
        screen.blit(nt, (side_rect.centerx - nt.get_width()//2,
                         side_rect.top + 34))

        ct = font_coin.render(f"Coins: {gm.coins}", True, C_GOLD)
        screen.blit(ct, (side_rect.centerx - ct.get_width()//2,
                         side_rect.top + 100))

        # REROLL ALL 버튼
        self.btn_reroll.rect.centerx = side_rect.centerx
        self.btn_reroll.rect.y       = side_rect.top + 132
        self.btn_reroll.rect.width   = side_rect.width - 14
        self.btn_reroll.draw(screen, disabled=(gm.reroll_tickets <= 0))
        h1 = font_hint.render("reroll all 4 dice", True, C_GRAY)
        screen.blit(h1, (side_rect.centerx - h1.get_width()//2,
                         self.btn_reroll.rect.bottom + 2))

        # BUY TICKET 버튼
        self.btn_buy.rect.centerx = side_rect.centerx
        self.btn_buy.rect.y       = side_rect.top + 210
        self.btn_buy.rect.width   = side_rect.width - 14
        self.btn_buy.draw(screen, disabled=(gm.coins < TICKET_BUY_COST))
        h2 = font_hint.render(f"{TICKET_BUY_COST} coins / ticket", True, C_GRAY)
        screen.blit(h2, (side_rect.centerx - h2.get_width()//2,
                         self.btn_buy.rect.bottom + 2))

        tip = font_hint.render("Boss drop: +1 ticket", True, (160, 100, 220))
        screen.blit(tip, (side_rect.centerx - tip.get_width()//2,
                          side_rect.bottom - 24))

        # ── 입장 버튼 ──
        self.btn_start.rect.centerx = sw // 2
        self.btn_start.rect.y       = sh - 70
        self.btn_start.draw(screen)

        font_ctrl = pygame.font.SysFont(None, 20)
        ctrl = font_ctrl.render(
            "WASD: Move    LClick: Attack    ESC: Quit", True, C_GRAY)
        screen.blit(ctrl, (sw//2 - ctrl.get_width()//2, sh - 22))