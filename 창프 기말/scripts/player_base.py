# scripts/player_base.py
# 스프라이트 시트를 직접 로드하여 프레임 리스트로 제공
# base64 없이 pygame.image.load + subsurface 방식 사용

import pygame

# ── 시트 로드 ──
player_sheet = pygame.image.load("./asset/Player/player.png")

FRAME_W, FRAME_H = 64, 64
COLS = 14

# ── 전체 프레임 추출 ──
_sheet_w, _sheet_h = player_sheet.get_size()
_ROWS  = _sheet_h // FRAME_H
_TOTAL = _ROWS * COLS

player_frames = []
for i in range(_TOTAL):
    row, col = divmod(i, COLS)
    rect = pygame.Rect(col * FRAME_W, row * FRAME_H, FRAME_W, FRAME_H)
    player_frames.append(player_sheet.subsurface(rect))

# ── 애니메이션별 프레임 리스트 ──
# 인덱스 계산: 행(row) * COLS + 열(col)
# 시트 레이아웃에 따라 아래 인덱스를 조정하세요.

# IDLE: 0번 행 0~7번 열 (8프레임)
IDLE_0   = [player_frames[i] for i in range(0 * COLS, 0 * COLS + 8)]

# WALK: 1번 행 0~7번 열 (8프레임)
MOVE_0   = [player_frames[i] for i in range(1 * COLS, 1 * COLS + 8)]

# ATTACK: 원본 코드의 인덱스 [26, 27, 28, 29] 유지 → 필요 시 8프레임으로 확장
# 26 = 1*14+12 (1번 행 12~13열 + 2번 행 0~1열)
# 8프레임이 필요하면: range(2*COLS, 2*COLS+8) 으로 변경
ATTACK_0 = [player_frames[i] for i in [26, 27, 28, 29]]
