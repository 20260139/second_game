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