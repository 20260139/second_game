# scripts/lobby.py
"""
소울나이트 스타일 로비.
- 중앙에 캐릭터 미리보기
- 좌측: 스탯 표시
- 우측: 업그레이드 버튼 (HP, 속도, 화력)
- 하단: 스테이지 입장 버튼
"""

import pygame, math, sys
sys.path.insert(0, '.')
from scripts import player_base

DRAW_SIZE = 80


def _load_idle_frames():
    """player_base.IDLE_0 프레임 리스트를 DRAW_SIZE로 스케일링하여 반환"""
    return [
        pygame.transform.scale(f.copy(), (DRAW_SIZE, DRAW_SIZE))
        for f in player_base.IDLE_0
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


class Button:
    def __init__(self, x, y, w, h, text, color=C_BTN, hover=C_BTN_HOV):
        self.rect  = pygame.Rect(x, y, w, h)
        self.text  = text
        self.color = color
        self.hover = hover
        self._font = None

    def draw(self, screen):
        if self._font is None:
            self._font = pygame.font.SysFont(None, 26)
        mx, my = pygame.mouse.get_pos()
        c = self.hover if self.rect.collidepoint(mx, my) else self.color
        pygame.draw.rect(screen, c, self.rect, border_radius=6)
        pygame.draw.rect(screen, C_BORDER, self.rect, 2, border_radius=6)
        t = self._font.render(self.text, True, C_WHITE)
        screen.blit(t, (self.rect.centerx - t.get_width()//2,
                        self.rect.centery - t.get_height()//2))

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))


class Lobby:
    def __init__(self, player):
        self.player  = player
        self._frames = None   # 늦은 로딩
        self._anim_i = 0
        self._anim_t = 0
        self._tick   = 0

        # 업그레이드 비용
        self.upgrade_cost = {"hp": 20, "speed": 30, "fire": 25}

        # 버튼 정의
        bx = 530
        self.btn_hp    = Button(bx, 180, 120, 36, f"HP UP  +20")
        self.btn_spd   = Button(bx, 240, 120, 36, f"SPD UP")
        self.btn_fire  = Button(bx, 300, 120, 36, f"FIRE UP")
        self.btn_start = Button(280, 500, 240, 50, "ENTER STAGE",
                                color=C_START, hover=C_START_H)

        # 파티클 (별 먼지)
        import random
        self._stars = [
            (random.randint(0,800), random.randint(0,600),
             random.uniform(0.2, 1.0), random.randint(1,3))
            for _ in range(80)
        ]

    def _ensure_frames(self):
        if self._frames is None:
            self._frames = _load_idle_frames()

    def handle_event(self, event, gm):
        if self.btn_start.is_clicked(event):
            gm.state = "STAGE1"
            return

        p = self.player
        if self.btn_hp.is_clicked(event):
            if gm.coins >= self.upgrade_cost["hp"]:
                gm.coins -= self.upgrade_cost["hp"]
                p.max_hp += 20
                p.hp      = p.max_hp
                self.upgrade_cost["hp"] += 10
                self.btn_hp.text = f"HP UP  Cost:{self.upgrade_cost['hp']}"

        if self.btn_spd.is_clicked(event):
            if gm.coins >= self.upgrade_cost["speed"]:
                gm.coins -= self.upgrade_cost["speed"]
                p.speed  += 0.4
                self.upgrade_cost["speed"] += 15
                self.btn_spd.text = f"SPD  Cost:{self.upgrade_cost['speed']}"

        if self.btn_fire.is_clicked(event):
            if gm.coins >= self.upgrade_cost["fire"]:
                gm.coins -= self.upgrade_cost["fire"]
                p.fire_rate = max(8, p.fire_rate - 3)
                self.upgrade_cost["fire"] += 15
                self.btn_fire.text = f"FIRE  Cost:{self.upgrade_cost['fire']}"

    def update(self, keys):
        self._ensure_frames()
        self._tick += 1
        self._anim_t += 1
        if self._anim_t >= 10:
            self._anim_t = 0
            self._anim_i = (self._anim_i + 1) % len(self._frames)

    def draw(self, screen, gm):
        """gm: GameManager 객체 (코인 수치 직접 참조)"""
        sw, sh = screen.get_size()

        # ── 배경 ──
        screen.fill(C_BG)

        # 별
        for sx, sy, br, sr in self._stars:
            alpha = int(180 * br * abs(math.sin(self._tick * 0.02 + br)))
            pygame.draw.circle(screen, (200, 190, 255), (sx, sy), sr)

        # ── 제목 ──
        font_title = pygame.font.SysFont(None, 62)
        t = font_title.render("SOUL  KNIGHT", True, C_GOLD)
        screen.blit(t, (sw//2 - t.get_width()//2, 30))

        # 부제
        font_sub = pygame.font.SysFont(None, 28)
        sub = font_sub.render("Choose your path, warrior.", True, C_GRAY)
        screen.blit(sub, (sw//2 - sub.get_width()//2, 88))

        # ── 캐릭터 패널 (중앙) ──
        panel_rect = pygame.Rect(220, 110, 260, 360)
        pygame.draw.rect(screen, C_PANEL, panel_rect, border_radius=12)
        pygame.draw.rect(screen, C_BORDER, panel_rect, 2, border_radius=12)

        # 캐릭터 스프라이트 (중앙 상단)
        if self._frames:
            img = self._frames[self._anim_i]
            float_y = int(math.sin(self._tick * 0.06) * 5)
            cx = panel_rect.centerx - DRAW_SIZE//2
            cy = panel_rect.top + 30 + float_y
            # 그림자
            shadow = pygame.Surface((60, 16), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0,0,0,80), (0,0,60,16))
            screen.blit(shadow, (cx+10, cy + DRAW_SIZE - 6))
            screen.blit(img, (cx, cy))

        # 캐릭터 이름
        font_name = pygame.font.SysFont(None, 30)
        nm = font_name.render("The Wanderer", True, C_GOLD)
        screen.blit(nm, (panel_rect.centerx - nm.get_width()//2,
                         panel_rect.top + 130))

        # 스탯 표시
        p    = self.player
        font_stat = pygame.font.SysFont(None, 24)
        stats = [
            ("HP",       f"{p.hp} / {p.max_hp}", C_RED),
            ("SPD",      f"{p.speed:.1f}",        C_GREEN),
            ("FIRE",     f"{p.fire_rate} tick",   C_BLUE),
            ("DMG",      f"{p.damage}",            C_GOLD),
        ]
        sy0 = panel_rect.top + 170
        for i, (label, val, col) in enumerate(stats):
            yl = sy0 + i*38
            pygame.draw.rect(screen, C_PANEL2, (panel_rect.left+16, yl, 228, 30), border_radius=4)
            lt = font_stat.render(label, True, C_GRAY)
            vt = font_stat.render(val,   True, col)
            screen.blit(lt, (panel_rect.left+24, yl+7))
            screen.blit(vt, (panel_rect.right-vt.get_width()-20, yl+7))

        # ── 업그레이드 패널 (우측) ──
        upg_rect = pygame.Rect(510, 110, 240, 280)
        pygame.draw.rect(screen, C_PANEL, upg_rect, border_radius=12)
        pygame.draw.rect(screen, C_BORDER, upg_rect, 2, border_radius=12)

        font_upg = pygame.font.SysFont(None, 28)
        upg_title = font_upg.render("UPGRADE", True, C_GOLD)
        screen.blit(upg_title, (upg_rect.centerx - upg_title.get_width()//2,
                                upg_rect.top + 10))

        # gm.coins 직접 참조
        coin_t = font_upg.render(f"Coins: {gm.coins}", True, C_GOLD)
        screen.blit(coin_t, (upg_rect.centerx - coin_t.get_width()//2,
                             upg_rect.top + 38))

        self.btn_hp.rect.x   = upg_rect.left + 10
        self.btn_spd.rect.x  = upg_rect.left + 10
        self.btn_fire.rect.x = upg_rect.left + 10
        self.btn_hp.rect.width   = 220
        self.btn_spd.rect.width  = 220
        self.btn_fire.rect.width = 220

        self.btn_hp.draw(screen)
        self.btn_spd.draw(screen)
        self.btn_fire.draw(screen)

        # 비용 힌트 (버튼 아래 표시)
        font_hint = pygame.font.SysFont(None, 20)
        hints = [
            (self.btn_hp,   f"Cost: {self.upgrade_cost['hp']} coins"),
            (self.btn_spd,  f"Cost: {self.upgrade_cost['speed']} coins"),
            (self.btn_fire, f"Cost: {self.upgrade_cost['fire']} coins"),
        ]
        for btn, hint in hints:
            ht = font_hint.render(hint, True, C_GRAY)
            screen.blit(ht, (btn.rect.left + 4, btn.rect.bottom + 2))

        # ── 입장 버튼 ──
        self.btn_start.rect.centerx = sw // 2
        self.btn_start.draw(screen)

        # 조작법 안내
        font_ctrl = pygame.font.SysFont(None, 22)
        ctrl = font_ctrl.render("WASD: Move    LClick: Shoot    ESC: Lobby", True, C_GRAY)
        screen.blit(ctrl, (sw//2 - ctrl.get_width()//2, sh - 30))
