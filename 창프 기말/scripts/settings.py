# scripts/settings.py
"""
설정 패널 — ESC 키로 열기/닫기
- BGM 볼륨 슬라이더
- SFX 볼륨 슬라이더
- 전체화면 토글
- 로비로 이동 (스테이지 진행 중일 때만 활성)
- 닫기
"""

import pygame

C_BG_OVERLAY = (0, 0, 0, 170)
C_PANEL      = (18, 14, 32)
C_BORDER     = (100, 70, 160)
C_TITLE      = (255, 210, 60)
C_WHITE      = (230, 230, 230)
C_GRAY       = (130, 120, 150)
C_BTN        = (45, 35, 75)
C_BTN_HOV    = (70, 55, 110)
C_BTN_RED    = (90, 25, 25)
C_BTN_RED_H  = (130, 40, 40)
C_BTN_GREEN  = (30, 90, 50)
C_BTN_GRN_H  = (45, 130, 70)
C_SLIDER_BG  = (30, 24, 50)
C_SLIDER_FG  = (100, 70, 200)
C_SLIDER_HOV = (140, 100, 255)
C_LOCKED     = (40, 35, 55)


class _Slider:
    """수평 슬라이더 (0.0 ~ 1.0)"""
    def __init__(self, x, y, w, h, value=1.0):
        self.rect  = pygame.Rect(x, y, w, h)
        self.value = max(0.0, min(1.0, value))
        self._dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._dragging = True
                self._update_value(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self._update_value(event.pos[0])

    def _update_value(self, mx):
        rel = (mx - self.rect.x) / self.rect.w
        self.value = max(0.0, min(1.0, rel))

    def draw(self, screen):
        # 트랙
        pygame.draw.rect(screen, C_SLIDER_BG, self.rect, border_radius=4)
        # 채움
        filled = pygame.Rect(self.rect.x, self.rect.y,
                             int(self.rect.w * self.value), self.rect.h)
        hov = self.rect.collidepoint(pygame.mouse.get_pos()) or self._dragging
        pygame.draw.rect(screen, C_SLIDER_HOV if hov else C_SLIDER_FG,
                         filled, border_radius=4)
        pygame.draw.rect(screen, C_BORDER, self.rect, 2, border_radius=4)
        # 핸들
        hx = self.rect.x + int(self.rect.w * self.value)
        hy = self.rect.centery
        pygame.draw.circle(screen, C_BORDER, (hx, hy), 8)
        pygame.draw.circle(screen, C_WHITE,  (hx, hy), 5)


class _Button:
    def __init__(self, x, y, w, h, text,
                 color=C_BTN, hover=C_BTN_HOV):
        self.rect  = pygame.Rect(x, y, w, h)
        self.text  = text
        self.color = color
        self.hover = hover

    def draw(self, screen, disabled=False):
        font = pygame.font.SysFont(None, 26)
        col  = C_LOCKED if disabled else (
            self.hover if self.rect.collidepoint(pygame.mouse.get_pos())
            else self.color)
        pygame.draw.rect(screen, col, self.rect, border_radius=7)
        pygame.draw.rect(screen, C_BORDER if not disabled else (50,45,65),
                         self.rect, 2, border_radius=7)
        tc = C_GRAY if disabled else C_WHITE
        t  = font.render(self.text, True, tc)
        screen.blit(t, (self.rect.centerx - t.get_width()//2,
                        self.rect.centery - t.get_height()//2))

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos))


class Settings:
    """설정 패널.  main.py 에서 settings.open() / settings.handle_event() / settings.draw() 호출."""

    def __init__(self):
        self.is_open      = False
        self._prev_state  = None   # 설정창 열기 전 상태 기억

        # 볼륨 (0.0 ~ 1.0)
        self.bgm_volume = 0.7
        self.sfx_volume = 0.8
        self.fullscreen  = False

        # UI 위젯 (draw 첫 호출 시 배치)
        self._built = False
        self._bgm_slider  = None
        self._sfx_slider  = None
        self._btn_fs      = None
        self._btn_lobby   = None
        self._btn_close   = None

    # ── 열기 / 닫기 ──────────────────────────────────────

    def open(self, prev_state):
        self.is_open     = True
        self._prev_state = prev_state
        self._built      = False   # 화면 크기 변경 대비 재빌드

    def close(self):
        self.is_open = False

    # ── 위젯 배치 (화면 크기 기반) ──────────────────────

    def _build(self, sw, sh):
        pw, ph = 420, 380
        px = sw//2 - pw//2
        py = sh//2 - ph//2

        sx  = px + 30
        sw2 = pw - 60
        row = py + 90

        self._panel_rect = pygame.Rect(px, py, pw, ph)

        self._bgm_slider = _Slider(sx, row,      sw2, 18, self.bgm_volume)
        self._sfx_slider = _Slider(sx, row + 70, sw2, 18, self.sfx_volume)

        bw, bh = 170, 38
        bx = px + pw//2 - bw//2
        self._btn_fs    = _Button(bx, row+145, bw, bh, self._fs_label())
        self._btn_lobby = _Button(bx, row+195, bw, bh, "RETURN TO LOBBY",
                                  color=C_BTN_RED, hover=C_BTN_RED_H)
        self._btn_close = _Button(bx, row+245, bw, bh, "RESUME",
                                  color=C_BTN_GREEN, hover=C_BTN_GRN_H)
        self._built = True

    def _fs_label(self):
        return "FULLSCREEN: ON" if self.fullscreen else "FULLSCREEN: OFF"

    # ── 이벤트 처리 ──────────────────────────────────────

    def handle_event(self, event, gm, lobby, screen):
        if not self.is_open:
            return

        sw, sh = screen.get_size()
        if not self._built:
            self._build(sw, sh)

        # 슬라이더
        self._bgm_slider.handle_event(event)
        self._sfx_slider.handle_event(event)
        self.bgm_volume = self._bgm_slider.value
        self.sfx_volume = self._sfx_slider.value
        self._apply_volumes()

        # 전체화면 토글
        if self._btn_fs.is_clicked(event):
            self.fullscreen = not self.fullscreen
            self._btn_fs.text = self._fs_label()
            if self.fullscreen:
                new_screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
            else:
                new_screen = pygame.display.set_mode((800, 600))
            self._built = False   # 재배치
            return new_screen

        # 로비 이동 (스테이지 중에만)
        in_stage = self._prev_state in ("STAGE1", "ROOM_CLEAR")
        if self._btn_lobby.is_clicked(event) and in_stage:
            lobby.on_enter_lobby()
            gm.stage = 1
            gm.state = "LOBBY"
            self.close()

        # 닫기
        if self._btn_close.is_clicked(event):
            gm.state = self._prev_state
            self.close()

        return None

    def _apply_volumes(self):
        try:
            pygame.mixer.music.set_volume(self.bgm_volume)
        except Exception:
            pass
        try:
            for ch in range(pygame.mixer.get_num_channels()):
                pygame.mixer.Channel(ch).set_volume(self.sfx_volume)
        except Exception:
            pass

    # ── 그리기 ───────────────────────────────────────────

    def draw(self, screen, gm):
        if not self.is_open:
            return

        sw, sh = screen.get_size()
        if not self._built:
            self._build(sw, sh)

        # 어두운 오버레이
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill(C_BG_OVERLAY)
        screen.blit(overlay, (0, 0))

        # 패널 배경
        px = self._panel_rect
        pygame.draw.rect(screen, C_PANEL,  px, border_radius=14)
        pygame.draw.rect(screen, C_BORDER, px, 2, border_radius=14)

        # 제목
        font_t = pygame.font.SysFont(None, 44)
        title  = font_t.render("S E T T I N G S", True, C_TITLE)
        screen.blit(title, (px.centerx - title.get_width()//2, px.y + 18))

        font_l = pygame.font.SysFont(None, 26)
        font_v = pygame.font.SysFont(None, 22)

        # BGM 슬라이더
        bl = font_l.render("BGM  VOLUME", True, C_WHITE)
        screen.blit(bl, (self._bgm_slider.rect.x,
                         self._bgm_slider.rect.y - 22))
        bv = font_v.render(f"{int(self.bgm_volume*100)}%", True, C_GRAY)
        screen.blit(bv, (self._bgm_slider.rect.right - bv.get_width(),
                         self._bgm_slider.rect.y - 22))
        self._bgm_slider.draw(screen)

        # SFX 슬라이더
        sl = font_l.render("SFX  VOLUME", True, C_WHITE)
        screen.blit(sl, (self._sfx_slider.rect.x,
                         self._sfx_slider.rect.y - 22))
        sv = font_v.render(f"{int(self.sfx_volume*100)}%", True, C_GRAY)
        screen.blit(sv, (self._sfx_slider.rect.right - sv.get_width(),
                         self._sfx_slider.rect.y - 22))
        self._sfx_slider.draw(screen)

        # 버튼
        self._btn_fs.draw(screen)

        in_stage = self._prev_state in ("STAGE1", "ROOM_CLEAR")
        self._btn_lobby.draw(screen, disabled=not in_stage)

        self._btn_close.draw(screen)

        # 안내
        hint = pygame.font.SysFont(None, 20).render(
            "G  to close", True, C_GRAY)
        screen.blit(hint, (px.centerx - hint.get_width()//2,
                            px.bottom - 22))