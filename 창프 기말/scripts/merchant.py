# scripts/merchant.py
"""
인게임 상인 팝업.
일반 방 클리어 시 일정 확률로 등장해 스탯 아이템 3개를 판매.
"""

import pygame, random, os, sys, math

sys.path.insert(0, '.')
try:
    from scripts.resource_path import resource_path
except Exception:
    def resource_path(p): return p

# ── 한글 폰트 헬퍼 ────────────────────────────────────────
# Windows / macOS / Linux 순서로 한글 지원 폰트를 탐색한다.
_FONT_CACHE = {}

def _get_font(size):
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]

    candidates = [
        # Windows
        "malgungothic", "malgun gothic", "gulim", "dotum", "batang",
        # macOS
        "applegothic", "nanum gothic", "nanumgothic",
        # Linux
        "noto sans cjk kr", "notosanscjkkr", "unfonts-core",
        # 공통 fallback
        "nanumgothic", "nanummyeongjo",
    ]
    font = None
    for name in candidates:
        try:
            f = pygame.font.SysFont(name, size)
            # 한글 한 글자를 렌더해서 실제로 지원하는지 확인
            test = f.render("가", True, (255, 255, 255))
            if test.get_width() > 4:   # 두부(tofu) □ 가 아닌지 체크
                font = f
                break
        except Exception:
            pass

    if font is None:
        # 마지막 수단: pygame 기본 폰트 (한글은 □ 로 나올 수 있지만 크래시 방지)
        font = pygame.font.SysFont(None, size)

    _FONT_CACHE[size] = font
    return font


# ── 색상 ─────────────────────────────────────────────────
C_OVERLAY  = (0,   0,   0,   170)
C_PANEL    = (22,  16,  38)
C_BORDER   = (200, 160,  50)
C_TITLE    = (255, 210,  60)
C_WHITE    = (230, 230, 230)
C_GRAY     = (140, 130, 160)
C_GOLD     = (255, 200,  40)
C_BTN      = (50,  38,  80)
C_BTN_HOV  = (80,  60, 120)
C_BTN_BUY  = (35,  90,  45)
C_BTN_BH   = (55, 130,  65)
C_BTN_SOLD = (40,  35,  55)
C_CLOSE    = (80,  30,  30)
C_CLOSE_H  = (120, 45,  45)

# ── 아이템 풀 ─────────────────────────────────────────────
# (표시명, stat_key, amount, price, 설명, 색상)
ITEM_POOL = [
    ("HP 포션 S",    "hp",   15, 12, "최대 HP +15",       (220,  80,  80)),
    ("HP 포션 M",    "hp",   25, 22, "최대 HP +25",       (220,  80,  80)),
    ("HP 포션 L",    "hp",   40, 35, "최대 HP +40",       (220,  80,  80)),
    ("스피드 룬 S",  "spd", 0.05,14, "이동속도 +0.05",    ( 80, 220, 100)),
    ("스피드 룬 M",  "spd", 0.10,26, "이동속도 +0.10",    ( 80, 220, 100)),
    ("공격력 보석 S","atk",   4, 15, "공격력 +4",         (255, 200,  60)),
    ("공격력 보석 M","atk",   7, 28, "공격력 +7",         (255, 200,  60)),
    ("공격력 보석 L","atk",  10, 40, "공격력 +10",        (255, 200,  60)),
    ("쿨다운 부적 S","cd",    1, 16, "공격 쿨다운 -1틱",  ( 80, 160, 255)),
    ("쿨다운 부적 M","cd",    2, 30, "공격 쿨다운 -2틱",  ( 80, 160, 255)),
    ("강화 결정",    "all",   0, 50, "모든 스탯 소폭 상승",(200, 140, 255)),
]

# ── 아이콘 그리기 (작은 심볼) ─────────────────────────────
def _draw_icon(surf, x, y, size, key, col):
    cx, cy = x + size//2, y + size//2
    if key == "hp":
        pygame.draw.rect(surf, col, (cx-2, cy-6, 4, 12), border_radius=1)
        pygame.draw.rect(surf, col, (cx-6, cy-2, 12, 4), border_radius=1)
    elif key == "spd":
        pts = [(cx-6,cy+4),(cx+2,cy-6),(cx+2,cy-1),(cx+8,cy-1),(cx,cy+7),(cx,cy+2),(cx-6,cy+4)]
        pygame.draw.polygon(surf, col, pts)
    elif key == "atk":
        pygame.draw.line(surf, col, (cx-5, cy+5), (cx+5, cy-5), 3)
        pygame.draw.polygon(surf, col, [(cx+3,cy-7),(cx+7,cy-3),(cx+7,cy-8)])
        pygame.draw.line(surf, col, (cx-7, cy+5), (cx-5, cy+7), 2)
    elif key == "cd":
        pygame.draw.circle(surf, col, (cx, cy), 6, 2)
        pygame.draw.line(surf, col, (cx, cy), (cx+4, cy-3), 2)
    elif key == "all":
        for i, c2 in enumerate([(220,80,80),(80,220,100),(255,200,60),(80,160,255)]):
            a = i / 4 * 2 * math.pi
            px2 = int(cx + 6 * math.cos(a))
            py2 = int(cy + 6 * math.sin(a))
            pygame.draw.circle(surf, c2, (px2, py2), 3)


# ── 상인 이미지 로더 ─────────────────────────────────────
# asset/Merchant/merchant.png 를 찾으면 로드, 없으면 None
_merchant_img_cache = {}   # {display_h: Surface or None}

def _load_merchant_image(display_h):
    """상인 이미지를 display_h 높이에 맞게 스케일해서 반환. 없으면 None."""
    global _merchant_img_cache
    display_h = int(display_h)
    if display_h in _merchant_img_cache:
        return _merchant_img_cache[display_h]

    path = resource_path("asset/Merchant/merchant.png")
    try:
        img = pygame.image.load(path).convert_alpha()
        # 비율 유지하며 높이를 display_h 에 맞춤
        iw, ih = img.get_size()
        s      = display_h / ih
        img    = pygame.transform.smoothscale(img, (int(iw * s), display_h))
        _merchant_img_cache[display_h] = img
    except Exception:
        _merchant_img_cache[display_h] = None   # 파일 없으면 None

    return _merchant_img_cache[display_h]


class MerchantItem:
    def __init__(self, data):
        self.name     = data[0]
        self.key      = data[1]
        self.amount   = data[2]
        self.price    = data[3]
        self.desc     = data[4]
        self.color    = data[5]
        self.sold     = False
        self.btn_rect = None


class Merchant:
    """인게임 상인 팝업."""

    APPEAR_CHANCE = 0.45   # 일반 방 클리어 시 등장 확률

    def __init__(self):
        self.is_open     = False
        self._items      = []
        self._close_rect = None

    # ── 열기 ──────────────────────────────────────────────

    def open(self):
        """랜덤 3개 아이템으로 상점 열기."""
        pool = random.sample(ITEM_POOL, min(3, len(ITEM_POOL)))
        self._items  = [MerchantItem(d) for d in pool]
        self.is_open = True

    def close(self):
        self.is_open = False

    # ── 아이템 적용 ───────────────────────────────────────

    def _apply(self, item, player):
        k, v = item.key, item.amount
        if k == "hp":
            player.max_hp += int(v)
            player.hp      = min(player.hp + int(v), player.max_hp)
        elif k == "spd":
            player.speed = round(player.speed + v, 3)
        elif k == "atk":
            player.damage += int(v)
        elif k == "cd":
            player.fire_rate = max(8, player.fire_rate - int(v))
        elif k == "all":
            player.max_hp    += 8;  player.hp = min(player.hp + 8, player.max_hp)
            player.speed      = round(player.speed + 0.03, 3)
            player.damage    += 2
            player.fire_rate  = max(8, player.fire_rate - 1)

    # ── 이벤트 ────────────────────────────────────────────

    def handle_event(self, event, gm, player):
        if not self.is_open:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 닫기 버튼
            if self._close_rect and self._close_rect.collidepoint(event.pos):
                self.close()
                return True

            # 아이템 구매 버튼
            for item in self._items:
                if item.btn_rect and item.btn_rect.collidepoint(event.pos):
                    if not item.sold and gm.coins >= item.price:
                        gm.coins -= item.price
                        self._apply(item, player)
                        item.sold = True
                    break

        return False

    # ── 그리기 ────────────────────────────────────────────

    def draw(self, screen, gm):
        if not self.is_open:
            return

        sw, sh = screen.get_size()

        # ── 오버레이 ──
        ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
        ov.fill(C_OVERLAY)
        screen.blit(ov, (0, 0))

        # ── 레이아웃 상수 (화면 크기에 비례해 스케일) ──
        # 기준 해상도 800x600 대비 배율
        scale  = min(sw / 800, sh / 600)
        # 패널은 상인 이미지 영역(왼쪽) + 아이템 영역(오른쪽) 으로 구성
        IMG_W  = int(160 * scale)   # 상인 이미지 열 너비
        ITEM_W = int(480 * scale)   # 아이템 카드 열 너비
        PW     = IMG_W + ITEM_W     # 전체 패널 너비
        PH     = int(440 * scale)
        PX     = sw // 2 - PW // 2
        PY     = sh // 2 - PH // 2

        # 패널 배경
        pygame.draw.rect(screen, C_PANEL,  (PX, PY, PW, PH), border_radius=14)
        pygame.draw.rect(screen, C_BORDER, (PX, PY, PW, PH), 2, border_radius=14)

        # ── 왼쪽: 상인 이미지 영역 ──────────────────────────
        img_area = pygame.Rect(PX, PY, IMG_W, PH)

        merchant_img = _load_merchant_image(PH - int(20*scale))
        if merchant_img:
            # 이미지가 있으면 영역 안에 하단 정렬로 표시
            iw, ih = merchant_img.get_size()
            ix = PX + IMG_W // 2 - iw // 2
            iy = PY + PH - ih - int(5*scale)
            # 이미지가 패널을 벗어나지 않도록 clip
            screen.set_clip(img_area)
            screen.blit(merchant_img, (ix, iy))
            screen.set_clip(None)
        else:
            # 이미지 없을 때: 점선 테두리 + 안내 문구
            placeholder_rect = pygame.Rect(PX + int(10*scale), PY + int(10*scale), IMG_W - int(20*scale), PH - int(20*scale))
            pygame.draw.rect(screen, (40, 30, 60), placeholder_rect, border_radius=8)
            pygame.draw.rect(screen, (70, 55, 100), placeholder_rect, 1, border_radius=8)
            pygame.draw.rect(screen, (55, 42, 80),
                             placeholder_rect.inflate(-4, -4), 1, border_radius=7)

            # 안내 아이콘 (사람 실루엣 느낌)
            mx = PX + IMG_W // 2
            my = PY + PH // 2 - int(10*scale)
            pygame.draw.circle(screen, (80, 60, 110), (mx, my - int(28*scale)), int(22*scale))
            pygame.draw.ellipse(screen, (80, 60, 110),
                                (mx - int(26*scale), my - int(6*scale), int(52*scale), int(38*scale)))

            fn = _get_font(max(8, int(14*scale)))
            path_hint = fn.render("asset/Merchant/", True, (90, 75, 120))
            fn2 = _get_font(max(8, int(14*scale)))
            path_hint2 = fn2.render("merchant.png", True, (90, 75, 120))
            screen.blit(path_hint,  (PX + IMG_W//2 - path_hint.get_width()//2,  PY + PH - int(52*scale)))
            screen.blit(path_hint2, (PX + IMG_W//2 - path_hint2.get_width()//2, PY + PH - int(34*scale)))

        # 세로 구분선
        pygame.draw.line(screen, C_BORDER,
                         (PX + IMG_W, PY + int(10*scale)),
                         (PX + IMG_W, PY + PH - int(10*scale)), 1)

        # ── 오른쪽: 제목 + 코인 ──────────────────────────────
        RX = PX + IMG_W   # 오른쪽 영역 시작 X

        font_title = _get_font(max(14, int(30 * scale)))
        title = font_title.render("MERCHANT", True, C_TITLE)
        screen.blit(title, (RX + ITEM_W // 2 - title.get_width() // 2, PY + int(12 * scale)))

        font_c = _get_font(max(11, int(22 * scale)))
        ct = font_c.render(f"Coins: {gm.coins}", True, C_GOLD)
        screen.blit(ct, (RX + ITEM_W - ct.get_width() - int(14 * scale), PY + int(16 * scale)))

        pygame.draw.line(screen, C_BORDER,
                         (RX + int(10*scale), PY + int(52*scale)), (PX + PW - int(10*scale), PY + int(52*scale)), 1)

        # ── 아이템 카드 3개 ──────────────────────────────────
        font_n = _get_font(max(11, int(22 * scale)))
        font_d = _get_font(max(9,  int(18 * scale)))
        font_p = _get_font(max(10, int(19 * scale)))

        cw = (ITEM_W - int(48*scale)) // 3   # 카드 하나의 너비
        ch = int(300 * scale)                 # 카드 높이
        CARD_TOP = PY + int(62 * scale)

        for i, item in enumerate(self._items):
            cx3 = RX + int(16*scale) + i * (cw + int(8*scale))
            cy3 = CARD_TOP

            # 카드 배경
            card_col = (28, 22, 48) if not item.sold else (20, 18, 30)
            pygame.draw.rect(screen, card_col,
                             (cx3, cy3, cw, ch), border_radius=10)
            bc = (100, 80, 160) if not item.sold else (50, 46, 65)
            pygame.draw.rect(screen, bc, (cx3, cy3, cw, ch), 2, border_radius=10)

            # ── 아이템 이미지 슬롯 (상단 영역) ──
            ITEM_IMG_SIZE = int(56 * scale)
            item_img_rect = pygame.Rect(
                cx3 + cw // 2 - ITEM_IMG_SIZE // 2,
                cy3 + int(10*scale),
                ITEM_IMG_SIZE, ITEM_IMG_SIZE
            )
            item_img = _load_item_image(item.key, ITEM_IMG_SIZE)
            if item_img and not item.sold:
                screen.blit(item_img, item_img_rect.topleft)
            elif item_img and item.sold:
                dark = item_img.copy()
                dark.fill((0, 0, 0, 140), special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(dark, item_img_rect.topleft)
            else:
                icon_sz = ITEM_IMG_SIZE
                icon_surf = pygame.Surface((icon_sz, icon_sz), pygame.SRCALPHA)
                if not item.sold:
                    _draw_icon(icon_surf, 0, 0, icon_sz, item.key, item.color)
                screen.blit(icon_surf, item_img_rect.topleft)

            # 이름
            nt = font_n.render(item.name, True,
                               item.color if not item.sold else C_GRAY)
            screen.blit(nt, (cx3 + cw//2 - nt.get_width()//2, cy3 + int(74*scale)))

            # 설명
            dt = font_d.render(item.desc, True, C_GRAY)
            screen.blit(dt, (cx3 + cw//2 - dt.get_width()//2, cy3 + int(100*scale)))

            # 가격
            if not item.sold:
                affordable = gm.coins >= item.price
                pc = C_GOLD if affordable else (160, 100, 60)
                pt = font_p.render(f"{item.price} G", True, pc)
            else:
                pt = font_p.render("SOLD", True, C_GRAY)
            screen.blit(pt, (cx3 + cw//2 - pt.get_width()//2, cy3 + int(126*scale)))

            # 구매 버튼
            bx3 = cx3 + int(8*scale)
            by3 = cy3 + ch - int(46*scale)
            bw3 = cw - int(16*scale)
            item.btn_rect = pygame.Rect(bx3, by3, bw3, int(36*scale))

            if item.sold:
                btn_c = C_BTN_SOLD
            elif gm.coins >= item.price:
                hov   = item.btn_rect.collidepoint(pygame.mouse.get_pos())
                btn_c = C_BTN_BH if hov else C_BTN_BUY
            else:
                btn_c = C_BTN_SOLD

            pygame.draw.rect(screen, btn_c, item.btn_rect, border_radius=7)
            pygame.draw.rect(screen, bc,    item.btn_rect, 2, border_radius=7)

            if item.sold:
                label = "SOLD"
            elif gm.coins >= item.price:
                label = "BUY"
            else:
                label = "코인 부족"
            lt = font_p.render(label, True, C_GRAY if item.sold else C_WHITE)
            screen.blit(lt, (item.btn_rect.centerx - lt.get_width()//2,
                             item.btn_rect.centery - lt.get_height()//2))

        # ── 닫기 버튼 ────────────────────────────────────────
        cw3, ch3 = int(160*scale), int(36*scale)
        self._close_rect = pygame.Rect(RX + ITEM_W//2 - cw3//2,
                                       PY + PH - int(52*scale), cw3, ch3)
        hov_c = self._close_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, C_CLOSE_H if hov_c else C_CLOSE,
                         self._close_rect, border_radius=8)
        pygame.draw.rect(screen, C_BORDER, self._close_rect, 2, border_radius=8)
        ct2 = font_c.render("LEAVE SHOP", True, C_WHITE)
        screen.blit(ct2, (self._close_rect.centerx - ct2.get_width()//2,
                          self._close_rect.centery - ct2.get_height()//2))

        # 안내
        fn_hint = _get_font(max(8, int(16 * scale)))
        ht = fn_hint.render("LEAVE SHOP 클릭 또는 모든 아이템 구매 시 계속", True, C_GRAY)
        screen.blit(ht, (RX + ITEM_W//2 - ht.get_width()//2, PY + PH - int(16*scale)))


# ── 아이템 이미지 캐시 ────────────────────────────────────
# 경로: asset/Item/<key>.png   예) asset/Item/hp.png
_item_img_cache = {}

def _load_item_image(key, size):
    cache_key = (key, size)
    if cache_key in _item_img_cache:
        return _item_img_cache[cache_key]

    path = resource_path(f"asset/Item/{key}.png")
    try:
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.smoothscale(img, (size, size))
        _item_img_cache[cache_key] = img
    except Exception:
        _item_img_cache[cache_key] = None

    return _item_img_cache[cache_key]