# scripts/player.py

import pygame
import base64
from io import BytesIO
import sys
sys.path.insert(0, '.')
from scripts import player_base

GRAVITY    = 0.55
JUMP_POWER = -12
MAX_FALL   = 14
CELL       = 64   # 스프라이트 원본 셀 크기
DRAW_SCALE = 96   # 렌더 크기

# 96px 스케일 기준 실제 캐릭터 픽셀 위치 (측정값)
# 원본 64px 셀: 캐릭터 픽셀 bbox ≈ x=18~43, y=18~48
# 96px 스케일: 시작점 ≈ (27, 27), 크기 ≈ 37×45
SPRITE_OFFSET_X = 27   # 스프라이트 좌상단 기준 캐릭터 픽셀 시작 X
SPRITE_OFFSET_Y = 27   # 스프라이트 좌상단 기준 캐릭터 픽셀 시작 Y
HITBOX_W        = 34   # 충돌박스 가로 (실제 캐릭터 폭에 맞춤)
HITBOX_H        = 44   # 충돌박스 세로 (실제 캐릭터 높이에 맞춤)


def _load_sheet():
    data  = base64.b64decode(player_base.IDLE_0)
    sheet = pygame.image.load(BytesIO(data)).convert_alpha()
    return sheet


def _crop_row(sheet, row, n_frames):
    frames = []
    for col in range(n_frames):
        rect  = pygame.Rect(col * CELL, row * CELL, CELL, CELL)
        frame = sheet.subsurface(rect).copy()
        frames.append(frame)
    return frames


class Player:

    ANIM_DEF = {
        # state : (row, n_frames, speed_per_frame)
        "IDLE"  : (0, 8, 8),
        "MOVE"  : (1, 8, 6),
        "GUARD" : (2, 4, 10),
        "JUMP"  : (3, 3, 6),
        "ATTACK": (4, 4, 5),   # 4프레임 × 5tick = 20tick 한 사이클
        "HIT"   : (6, 2, 8),
    }

    def __init__(self):

        sheet = _load_sheet()

        self._frames = {}
        for state, (row, n, _) in self.ANIM_DEF.items():
            self._frames[state] = _crop_row(sheet, row, n)

        self._anim_state = "IDLE"
        self._anim_index = 0
        self._anim_timer = 0

        # 위치 = 충돌박스 좌상단
        self.x = 100.0
        self.y = 200.0

        self.width  = HITBOX_W
        self.height = HITBOX_H

        self.vx = 0.0
        self.vy = 0.0
        self.speed = 4

        self.hp     = 100
        self.max_hp = 100

        self.flip = 1   # 1=오른쪽, -1=왼쪽

        self.state      = "IDLE"
        self.on_ground  = False
        self.jump_count = 0

        # ── 공격 플래그 ──────────────────────────────────
        # is_attack    : 현재 공격 애니메이션 재생 중
        # attack_fired : 이번 MOUSEBUTTONDOWN 이벤트로 이미 공격을 발동했는가
        #                (이벤트 기반으로 처리하므로 사실상 매 이벤트마다 리셋됨)
        self.is_attack       = False
        self.attack_cooldown = 0   # 공격 후 재공격 가능까지 대기 프레임

        self.hit_timer = 0

    # ── 충돌 박스 ─────────────────────────────────────────
    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    # ── 매 프레임 키 입력 (이동·상태 결정) ──────────────────
    def input(self, keys):
        """
        이동과 상태 결정만 담당.
        공격은 이벤트 기반 → on_mouse_click() 으로 별도 처리.
        """
        moving = False

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx   = -self.speed
            self.flip  = -1
            moving     = True
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx   = self.speed
            self.flip  = 1
            moving     = True
        else:
            self.vx *= 0.75
            if abs(self.vx) < 0.5:
                self.vx = 0

        # ── 상태 결정 ─────────────────────────────────────
        # 우선순위: HIT > ATTACK > JUMP > MOVE > IDLE
        # ATTACK은 is_attack 플래그로만 판단
        # (플래그는 _update_anim 에서 애니메이션 1사이클 끝날 때 해제)
        if self.hit_timer > 40:
            self.state = "HIT"
        elif self.is_attack:
            self.state = "ATTACK"
        elif not self.on_ground:
            self.state = "JUMP"
        elif moving:
            self.state = "MOVE"
        else:
            self.state = "IDLE"

    # ── 마우스 클릭 이벤트 (MOUSEBUTTONDOWN 에서 호출) ──────
    def on_mouse_click(self, button):
        """
        main.py 이벤트 루프의 MOUSEBUTTONDOWN 에서 호출.
        button == 1 이 좌클릭.
        get_pressed() 가 아닌 이벤트로 받으므로 딱 한 번만 발동.
        """
        if button == 1:
            self._try_attack()

    def _try_attack(self):
        """공격 발동 — 이미 공격 중이거나 쿨다운 남아있으면 무시"""
        if self.is_attack or self.attack_cooldown > 0:
            return
        self.is_attack = True
        # attack_cooldown 은 애니메이션이 끝난 뒤 _update_anim 에서 설정

    def jump(self):
        """KEYDOWN 이벤트에서 호출 — 2단 점프"""
        if self.on_ground:
            self.vy         = JUMP_POWER
            self.on_ground  = False
            self.jump_count = 1
        elif self.jump_count < 2:
            self.vy         = JUMP_POWER * 0.85
            self.jump_count += 1

    # ── 물리 & 충돌 ───────────────────────────────────────
    def update(self, platforms):

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.hit_timer > 0:
            self.hit_timer -= 1

        # 중력
        self.vy += GRAVITY
        if self.vy > MAX_FALL:
            self.vy = MAX_FALL

        # X 이동 + 벽 충돌
        self.x += self.vx
        rect = self.get_rect()
        for p in platforms:
            if rect.colliderect(p):
                if self.vx > 0:
                    self.x = p.left - self.width
                elif self.vx < 0:
                    self.x = p.right
                self.vx = 0

        # Y 이동 + 바닥/천장 충돌
        self.on_ground = False
        self.y += self.vy
        rect = self.get_rect()
        for p in platforms:
            if rect.colliderect(p):
                if self.vy > 0:
                    self.y          = p.top - self.height
                    self.vy         = 0
                    self.on_ground  = True
                    self.jump_count = 0
                elif self.vy < 0:
                    self.y  = p.bottom
                    self.vy = 0

        self._update_anim()

    # ── 애니메이션 ─────────────────────────────────────────
    def _update_anim(self):
        """
        ATTACK 은 4프레임을 정확히 1회만 재생.
        마지막 프레임이 끝나면 is_attack=False, attack_cooldown 시작.
        나머지 상태는 루프 재생.
        """
        _, n_frames, speed = self.ANIM_DEF[self.state]

        # 상태가 바뀌면 처음부터
        if self._anim_state != self.state:
            self._anim_state = self.state
            self._anim_index = 0
            self._anim_timer = 0

        self._anim_timer += 1
        if self._anim_timer >= speed:
            self._anim_timer = 0
            next_idx = self._anim_index + 1

            if self._anim_state == "ATTACK":
                if next_idx >= n_frames:
                    # 1사이클 완료 → 공격 종료
                    self.is_attack       = False
                    self.attack_cooldown = 20  # 재공격 대기
                    self._anim_index     = 0
                else:
                    self._anim_index = next_idx
            else:
                self._anim_index = next_idx % n_frames

    # ── 공격 판정 박스 ─────────────────────────────────────
    def get_attack_rect(self):
        if not self.is_attack:
            return None
        if self.flip == 1:
            return pygame.Rect(int(self.x) + self.width, int(self.y) + 8, 36, 24)
        else:
            return pygame.Rect(int(self.x) - 36, int(self.y) + 8, 36, 24)

    # ── 피해 ──────────────────────────────────────────────
    def damage(self, amount):
        if self.hit_timer > 0:
            return
        self.hp       -= amount
        self.hit_timer = 60
        if self.hp < 0:
            self.hp = 0

    # ── 그리기 ─────────────────────────────────────────────
    def draw(self, screen, cam_x, cam_y):

        # 피격 깜빡임
        if self.hit_timer > 0 and self.hit_timer <= 40 and (self.hit_timer // 4) % 2 == 0:
            return

        frame        = self._frames[self._anim_state][self._anim_index]
        frame_scaled = pygame.transform.scale(frame, (DRAW_SCALE, DRAW_SCALE))

        if self.flip == -1:
            frame_scaled = pygame.transform.flip(frame_scaled, True, False)

        # 충돌박스 좌상단(player.x, player.y)에서
        # 스프라이트 내 캐릭터 픽셀 시작점(SPRITE_OFFSET_X, SPRITE_OFFSET_Y)을 빼서 정렬
        draw_x = int(self.x) - cam_x - SPRITE_OFFSET_X
        draw_y = int(self.y) - cam_y - SPRITE_OFFSET_Y

        screen.blit(frame_scaled, (draw_x, draw_y))

    # ── 디버그: 충돌박스 시각화 (필요시 활성화) ──────────────
    def draw_debug(self, screen, cam_x, cam_y):
        r = self.get_rect().move(-cam_x, -cam_y)
        pygame.draw.rect(screen, (0, 255, 0), r, 1)
        ar = self.get_attack_rect()
        if ar:
            pygame.draw.rect(screen, (255, 0, 0), ar.move(-cam_x, -cam_y), 1)

    # ── HUD ───────────────────────────────────────────────
    def draw_hud(self, screen):

        font  = pygame.font.SysFont(None, 24)
        label = font.render("HP", True, (200, 200, 200))
        screen.blit(label, (20, 18))

        pygame.draw.rect(screen, (60, 20, 20), (44, 18, 160, 14))

        ratio = max(self.hp / self.max_hp, 0)
        r_ch  = int(220 * (1 - ratio) + 60  * ratio)
        g_ch  = int(60  * (1 - ratio) + 200 * ratio)
        pygame.draw.rect(screen, (r_ch, g_ch, 50), (44, 18, int(160 * ratio), 14))

        pygame.draw.rect(screen, (200, 200, 200), (44, 18, 160, 14), 1)
