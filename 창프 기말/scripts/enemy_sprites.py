# scripts/enemy_sprites.py
# 적 스프라이트 로드.
# asset/Enemy/ 에 이미지 파일이 있으면 파일을 사용하고,
# 없으면 내장 base64 데이터를 사용한다.
#
# 새 적 이미지 추가 방법:
#   1. asset/Enemy/파일명.png 배치
#   2. 아래 _load() 호출 추가:
#      YOUR_WALK = _load("asset/Enemy/파일명.png", YOUR_B64, 4)

import pygame, base64, os, sys
from io import BytesIO

sys.path.insert(0, '.')
from scripts.resource_path import resource_path

CELL = 32

def _load(rel_path, b64_fallback, n_frames):
    """파일 존재 시 파일 로드, 없으면 base64 fallback."""
    path = resource_path(rel_path)
    try:
        sheet = pygame.image.load(path)
    except (FileNotFoundError, pygame.error):
        raw   = base64.b64decode(b64_fallback)
        sheet = pygame.image.load(BytesIO(raw))
    w = sheet.get_width() // n_frames
    h = sheet.get_height()
    return [sheet.subsurface(pygame.Rect(i*w, 0, w, h)).copy()
            for i in range(n_frames)]

# ── 슬라임
_SLIME_B64 = "iVBORw0KGgoAAAANSUhEUgAAAIAAAAAgCAYAAADaInAlAAACW0lEQVR4nO2aMZKDIBSGzc72OQKtdRqvEZttvUaOsNew3UavYZOaliPkBNkKh+ADHk9ARb4ZZ5KQ9f/J+5+raFUVCoVCoVAoFE7HZWsDBX/qR/02jfFf7lXTEoCDYCu6CUwYSAEImcAjknL+kFZ9r43f5yP38oQ2GyuBR2GL+auasuj3+j7p3xv52ID6ShhMXpwGYyeQQk4diNGVekMzzOP9q/8IwsjHRh1vp3bhB/JhNZYigVhy7UCbLlR4nf7VT921A/WrahkE3YfRVKoEusi9A311GWPzayHEIgD6uMsHaChlAm2coQN9tNXiSoQQznGbhy+TAROMsXmjjGMP5aZO6K5do//gMhRDM8yb+ndUXYhU80/FIo2pEwhxpg60aYfWhzwsjgBbc7YOdKEWTy22fO8zDvERACiBIZH7xRQB04GMscp0AiTfQ/8OjJo7mr8JIcS8UcZ1nEeA2AncO3uYfzu1i/2on7nGbXz7mnElC5s8iBQdyEde1Y/6TV0jiDl/F66CUsKGOgeImUCMtiTHDlSRoYTWMkIAnYR6HQFiJNCX3DpwDc+f5/z69ncj7cN5GRgSymWQCrTS5jMewsMaMJei0PqHjiy8WnToM0hb1/c+B4CM2IRDkmMH6vBffnFdJUBaWH3nvYDUCTTpn6UD1/jAQLobGKMI1JU4G74dGMMDllD3QiiaNt1VnRDKhK9uTh3o4wPjJ+gTQSkSaNM9QwdSvKD1QzwTuKf78RT23oEUNnkqeC9P5HjpH6ADt4Zk8AzP5Pl6iqUVm8OYzbUDt+aQP1BOHbg1/1+a7Nv234N3AAAAAElFTkSuQmCC"
SLIME_WALK = _load("asset/Enemy/slime.png", _SLIME_B64, 4)

# ── 박쥐
_BAT_B64   = "iVBORw0KGgoAAAANSUhEUgAAAIAAAAAgCAYAAADaInAlAAACX0lEQVR4nO2YoXrDIBCA6b6p6s6ip6Pbd+gbzGSmog8zERXTN9g7tDq6Grvq2syMfoQccByQNN/uN/tGE/47chCCEAzDMAzDMAxjspfHfs5+2D+vP0sQfP9z3/9SMoi5K9h1X101Uf1Nlb8rrpL+YAF8q68VJQh9vb6fSm5/7MOfOn87vtJ+1Apgd5rrulhS/Xpw2+5AKsrS+eu4UleCGD+qAMwqCnVu/p46+3P566rpY2d+Tj8FM+aS/ldKcHt57G/3+6h9s15TuivqT3nwOfyp1FXT2ytWTv9gBfANll1Ntsz+31d9lIdC8cd6njX/umr6nH6T0Qrge0/qqjvL7tF2ko0QQogPdXi07VQFylJnY4zf5Qq9/+fOv+0OYOHWVdNfVZfkhxglacv1QGw3dW/LfexUJS63FtzUUDZhFP+7HA8EtgDs66fMHyoA6OFj/T6CewAdzFV1A/mbUuJHysG1ZttZduJT5n3/RvsFfia4WHL+q1u4T9RXgK4+U2T+dbXZ91HRs28u/9z5U/32uEGMCgCzPOsqMysQaoPw9Y/dI1D9mNzmzB97TYpfiOE4R30GnmTz2GxAIrMtZiOicW2A9Awo7Q+xRD80nmaBga8AXwXqXaf5P9QW2y+WFD+W/5Q/6SAIEqQOusa1Ckzlx7Bkv12EqE2g/pxqLy1O8ncd9BmGut8KMoc/ZfZNnb8Qw3hz+aExcBaAa8BCQbh+z7H8pfijPf8k/+CBhBm4+VlRb2uv3DyEgM6zMbC/vJ98IucDcwJFhf15/eRAoUBKJs7+5/IzDMMwDMMwDLNUfgHGHJ1eLp3iygAAAABJRU5ErkJggg=="
BAT_WALK   = _load("asset/Enemy/bat.png",   _BAT_B64,   4)

# ── 궁수
_ARCHER_B64 = "iVBORw0KGgoAAAANSUhEUgAAAIAAAAAgCAYAAADaInAlAAACIElEQVR4nO2aIXeDMBSFLztT1dFodNUEqqJ6amKqoqq6gp+AQE9VVFVMVVdMRUyh0ejoWSY22o6WkeRAQh65hgPNyf3e4fUlIQmgoOQ5rGTbpscyUOnbBQaK3g96OF5U5BNg4vIJMHH5BJi4pCYL65hVAMDYTLpjIb4AADsuepkM2WSg7P2oAlN3bFM2GSh6+yFg4ho8AfbrSHr9SpFh7N7S49M+ea7iODrfLzYHfLy9tt5zXmCVHnv9GGKTgaq3VgVYbA7/Xk3IJgMlb60EqLOt7WpCNhkoeWvPAZqGJl/+GBioeEsnwCo9BpwXUm2HGP9tM1D1VqoAIs/RBcJ5AZHnKt0qySYDRW/pBMiWYRXPQ0QQrSCcF4ggEM9DZEv57UsXGKh6S5WKGuBaBdhtQ1EgYpfnPC+xPV32pj/f19XTy06rNNpkoOzd+Sn4HgAARBC3jdlfsHgeIgOqaxAd2WSg7t3rl8BC3AEzLJsMLnr3mgARu1OaDMsmg4vefjNo4uo9Afww4JZ3ZwJsT2XA81K6w4ixM0hzJqormwzUvaUqgA4Iz0uwcNbbdqhNBsre0ieCtqcyyIAK+FlitKmG7eOfPyYGqt7a69O234Z48WNjmKr3WUnMquT3sKLMc5McJhhsxt93zM4uA+uA08bJ1+Y9RbXFrJMEziZAl0xWIlMaIialY+GuiGoVGCIu5QrQVnqvn1H899WiFj/ZIcBLTt9odmDuMaygfAAAAABJRU5ErkJggg=="
ARCHER_WALK = _load("asset/Enemy/archer.png", _ARCHER_B64, 4)

# ── 새 적 추가 예시 ──────────────────────────────────────────
# KNIGHT_WALK = _load("asset/Enemy/knight.png", "", 4)

# ══════════════════════════════════════════════════════════
#  절차적 스프라이트 (파일 없이 pygame 도형으로 생성)
#  각 4프레임, 32×32px
# ══════════════════════════════════════════════════════════

import math as _math

def _proc_surface():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    return s


# ── 고블린 (2층) ─────────────────────────────────────────
def _make_goblin_frames():
    frames = []
    for fi in range(4):
        s  = _proc_surface()
        bob = [0, -1, -2, -1][fi]
        cx, cy = 16, 16 + bob

        # 몸통 (녹색 계란형)
        pygame.draw.ellipse(s, (40, 140, 40), (cx-7, cy-6, 14, 12))
        pygame.draw.ellipse(s, (80, 200, 60), (cx-7, cy-6, 14, 12), 1)

        # 머리
        pygame.draw.circle(s, (50, 160, 50), (cx, cy-10), 7)
        pygame.draw.circle(s, (90, 210, 70), (cx, cy-10), 7, 1)

        # 귀 (뾰족)
        pygame.draw.polygon(s, (40, 140, 40),
                            [(cx-7, cy-14), (cx-10, cy-19), (cx-4, cy-13)])
        pygame.draw.polygon(s, (40, 140, 40),
                            [(cx+7, cy-14), (cx+10, cy-19), (cx+4, cy-13)])

        # 눈 (노랑)
        for ex in [cx-3, cx+3]:
            pygame.draw.circle(s, (255, 230, 0), (ex, cy-11), 2)
            pygame.draw.circle(s, (0, 0, 0), (ex, cy-11), 1)

        # 다리
        leg = [0, 1, 0, -1][fi]
        pygame.draw.line(s, (30, 110, 30), (cx-4, cy+6), (cx-4, cy+12+leg), 2)
        pygame.draw.line(s, (30, 110, 30), (cx+4, cy+6), (cx+4, cy+12-leg), 2)

        frames.append(s)
    return frames

_GOBLIN_WALK = None
def _get_goblin_walk():
    global _GOBLIN_WALK
    if _GOBLIN_WALK is None:
        _GOBLIN_WALK = _make_goblin_frames()
    return _GOBLIN_WALK


# ── 해골 (3층) ───────────────────────────────────────────
def _make_skeleton_frames():
    frames = []
    for fi in range(4):
        s  = _proc_surface()
        bob = [0, -1, -2, -1][fi]
        cx, cy = 16, 16 + bob

        # 몸통 (흰 뼈대)
        pygame.draw.rect(s, (220, 220, 210), (cx-5, cy-4, 10, 10))
        pygame.draw.rect(s, (180, 180, 170), (cx-5, cy-4, 10, 10), 1)

        # 갈비뼈
        for ry in [cy-2, cy+1, cy+4]:
            pygame.draw.line(s, (180, 180, 170), (cx-5, ry), (cx-7, ry), 1)
            pygame.draw.line(s, (180, 180, 170), (cx+5, ry), (cx+7, ry), 1)

        # 두개골
        pygame.draw.circle(s, (230, 230, 220), (cx, cy-10), 7)
        pygame.draw.circle(s, (180, 180, 170), (cx, cy-10), 7, 1)

        # 눈 (검정 구멍)
        for ex in [cx-3, cx+3]:
            pygame.draw.ellipse(s, (10, 10, 10), (ex-2, cy-12, 4, 4))

        # 이빨
        for tx in [cx-2, cx, cx+2]:
            pygame.draw.rect(s, (240, 240, 230), (tx-1, cy-5, 2, 3))

        # 다리 (뼈)
        leg = [0, 1, 0, -1][fi]
        pygame.draw.line(s, (200, 200, 190), (cx-3, cy+6), (cx-3, cy+13+leg), 2)
        pygame.draw.line(s, (200, 200, 190), (cx+3, cy+6), (cx+3, cy+13-leg), 2)

        frames.append(s)
    return frames

_SKELETON_WALK = None
def _get_skeleton_walk():
    global _SKELETON_WALK
    if _SKELETON_WALK is None:
        _SKELETON_WALK = _make_skeleton_frames()
    return _SKELETON_WALK


# ── 다크나이트 (4층) ─────────────────────────────────────
def _make_dknight_frames():
    frames = []
    for fi in range(4):
        s  = _proc_surface()
        bob = [0, -1, 0, 1][fi]
        cx, cy = 16, 16 + bob

        # 갑옷 몸통 (짙은 남보라)
        pygame.draw.rect(s, (35, 25, 60), (cx-8, cy-6, 16, 14), border_radius=3)
        pygame.draw.rect(s, (80, 60, 130), (cx-8, cy-6, 16, 14), 2, border_radius=3)

        # 투구
        pygame.draw.rect(s, (30, 20, 55), (cx-7, cy-14, 14, 10), border_radius=2)
        pygame.draw.rect(s, (70, 50, 120), (cx-7, cy-14, 14, 10), 2, border_radius=2)

        # 눈 (빨간 불꽃)
        for ex in [cx-3, cx+3]:
            pygame.draw.circle(s, (200, 0, 0), (ex, cy-10), 2)
            pygame.draw.circle(s, (255, 80, 0), (ex, cy-10), 1)

        # 어깨 장식
        for sx2, sign in [(cx-9, -1), (cx+9, 1)]:
            pygame.draw.circle(s, (60, 45, 100), (sx2, cy-5), 4)
            pygame.draw.circle(s, (100, 80, 160), (sx2, cy-5), 4, 1)

        # 검 (오른쪽)
        sw = [0, 1, 0, -1][fi]
        pygame.draw.line(s, (160, 160, 180), (cx+8, cy-8+sw), (cx+13, cy+6+sw), 2)
        pygame.draw.line(s, (100, 80, 130), (cx+7, cy-4), (cx+10, cy-4), 2)

        # 다리
        leg = [0, 1, 0, -1][fi]
        pygame.draw.rect(s, (25, 18, 45), (cx-7, cy+8, 6, 7+leg), border_radius=1)
        pygame.draw.rect(s, (25, 18, 45), (cx+1, cy+8, 6, 7-leg), border_radius=1)

        frames.append(s)
    return frames

_DKNIGHT_WALK = None
def _get_dknight_walk():
    global _DKNIGHT_WALK
    if _DKNIGHT_WALK is None:
        _DKNIGHT_WALK = _make_dknight_frames()
    return _DKNIGHT_WALK


# ── 데몬 (5층) ───────────────────────────────────────────
def _make_demon_frames():
    frames = []
    for fi in range(4):
        s  = _proc_surface()
        bob = [0, -2, -3, -2][fi]
        cx, cy = 16, 17 + bob

        # 날개 (붉은 박쥐형)
        for sign in [-1, 1]:
            wing = [
                (cx, cy-4),
                (cx + sign*14, cy-12),
                (cx + sign*12, cy+2),
                (cx + sign*6,  cy+4),
            ]
            pygame.draw.polygon(s, (120, 10, 10), wing)
            pygame.draw.polygon(s, (200, 40, 40), wing, 1)

        # 몸통 (짙은 빨강)
        pygame.draw.ellipse(s, (140, 15, 15), (cx-7, cy-6, 14, 14))
        pygame.draw.ellipse(s, (220, 50, 50), (cx-7, cy-6, 14, 14), 1)

        # 머리
        pygame.draw.circle(s, (150, 20, 20), (cx, cy-10), 7)
        pygame.draw.circle(s, (220, 60, 60), (cx, cy-10), 7, 1)

        # 뿔
        pygame.draw.polygon(s, (80, 5, 5),
                            [(cx-5, cy-15), (cx-8, cy-22), (cx-2, cy-15)])
        pygame.draw.polygon(s, (80, 5, 5),
                            [(cx+5, cy-15), (cx+8, cy-22), (cx+2, cy-15)])

        # 눈 (노란 불꽃)
        pulse = [0, 1, 2, 1][fi]
        for ex in [cx-3, cx+3]:
            pygame.draw.circle(s, (255, 200+pulse*10, 0), (ex, cy-11), 2)
            pygame.draw.circle(s, (255, 255, 100), (ex, cy-11), 1)

        # 꼬리
        t = [0, 1, 0, -1][fi]
        pygame.draw.arc(s, (160, 20, 20),
                        (cx-4, cy+5+t, 10, 8), 0, _math.pi, 2)

        frames.append(s)
    return frames

_DEMON_WALK = None
def _get_demon_walk():
    global _DEMON_WALK
    if _DEMON_WALK is None:
        _DEMON_WALK = _make_demon_frames()
    return _DEMON_WALK


# ── 오크 (3층 추가) ──────────────────────────────────────
def _make_orc_frames():
    frames = []
    for fi in range(4):
        s  = _proc_surface()
        bob = [0, -1, -2, -1][fi]
        cx, cy = 16, 17 + bob

        # 몸통 (넓고 두꺼운 녹갈색)
        pygame.draw.ellipse(s, (60, 100, 40), (cx-9, cy-5, 18, 14))
        pygame.draw.ellipse(s, (90, 140, 60), (cx-9, cy-5, 18, 14), 1)

        # 머리 (크고 네모에 가까움)
        pygame.draw.rect(s, (70, 115, 45), (cx-8, cy-16, 16, 13), border_radius=3)
        pygame.draw.rect(s, (100, 150, 65), (cx-8, cy-16, 16, 13), 1, border_radius=3)

        # 엄니 (흰 아래 이빨)
        pygame.draw.polygon(s, (230, 230, 210),
                            [(cx-4, cy-5), (cx-2, cy-5), (cx-3, cy-2)])
        pygame.draw.polygon(s, (230, 230, 210),
                            [(cx+2, cy-5), (cx+4, cy-5), (cx+3, cy-2)])

        # 눈 (작고 빨간)
        for ex in [cx-4, cx+4]:
            pygame.draw.circle(s, (200, 30, 30), (ex, cy-11), 2)

        # 팔 (굵음)
        arm = [0, 1, 0, -1][fi]
        pygame.draw.line(s, (50, 90, 35), (cx-9, cy-3), (cx-14, cy+3+arm), 3)
        pygame.draw.line(s, (50, 90, 35), (cx+9, cy-3), (cx+14, cy+3-arm), 3)

        # 도끼 (오른손)
        ax, ay = cx+14, cy+3
        pygame.draw.line(s, (160, 140, 120), (ax, ay-arm), (ax+2, ay+5-arm), 2)
        pygame.draw.polygon(s, (180, 160, 130),
                            [(ax+1, ay-arm), (ax+5, ay-3-arm), (ax+5, ay+1-arm)])

        # 다리
        leg = [0, 1, 0, -1][fi]
        pygame.draw.rect(s, (50, 85, 35), (cx-7, cy+9, 6, 6+leg), border_radius=1)
        pygame.draw.rect(s, (50, 85, 35), (cx+1, cy+9, 6, 6-leg), border_radius=1)

        frames.append(s)
    return frames

_ORC_WALK = None
def _get_orc_walk():
    global _ORC_WALK
    if _ORC_WALK is None:
        _ORC_WALK = _make_orc_frames()
    return _ORC_WALK


# ── 뱀파이어 (4층 추가) ──────────────────────────────────
def _make_vampire_frames():
    frames = []
    for fi in range(4):
        s  = _proc_surface()
        bob = [0, -2, -4, -2][fi]
        cx, cy = 16, 16 + bob

        # 망토 (짙은 빨강)
        cape = [
            (cx-10, cy+2), (cx-13, cy+14),
            (cx, cy+12),
            (cx+13, cy+14), (cx+10, cy+2),
            (cx+7, cy-4), (cx, cy-6), (cx-7, cy-4),
        ]
        pygame.draw.polygon(s, (100, 0, 0), cape)
        pygame.draw.polygon(s, (180, 20, 20), cape, 1)

        # 망토 안쪽 (보라)
        inner = [
            (cx-7, cy+2), (cx-9, cy+13),
            (cx, cy+11),
            (cx+9, cy+13), (cx+7, cy+2),
        ]
        pygame.draw.polygon(s, (60, 0, 80), inner)

        # 머리
        pygame.draw.circle(s, (200, 180, 190), (cx, cy-10), 7)
        pygame.draw.circle(s, (150, 100, 120), (cx, cy-10), 7, 1)

        # 머리카락 (검정)
        pygame.draw.ellipse(s, (20, 10, 30), (cx-7, cy-18, 14, 10))

        # 귀 (뾰족)
        pygame.draw.polygon(s, (20, 10, 30),
                            [(cx-6, cy-15), (cx-9, cy-20), (cx-3, cy-14)])
        pygame.draw.polygon(s, (20, 10, 30),
                            [(cx+6, cy-15), (cx+9, cy-20), (cx+3, cy-14)])

        # 눈 (빨간 빛)
        pulse = [0, 1, 2, 1][fi]
        for ex in [cx-3, cx+3]:
            pygame.draw.circle(s, (200+pulse*10, 0, 20), (ex, cy-11), 2)
            pygame.draw.circle(s, (255, 80, 80), (ex, cy-11), 1)

        # 엄니
        pygame.draw.polygon(s, (240, 230, 235),
                            [(cx-2, cy-5), (cx-1, cy-5), (cx-1, cy-2)])
        pygame.draw.polygon(s, (240, 230, 235),
                            [(cx+1, cy-5), (cx+2, cy-5), (cx+2, cy-2)])

        frames.append(s)
    return frames

_VAMPIRE_WALK = None
def _get_vampire_walk():
    global _VAMPIRE_WALK
    if _VAMPIRE_WALK is None:
        _VAMPIRE_WALK = _make_vampire_frames()
    return _VAMPIRE_WALK
