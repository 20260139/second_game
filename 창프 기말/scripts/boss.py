# scripts/boss.py
"""
보스: 다크 리치 (Dark Lich)

애니메이션: fallback 절차적 스프라이트 (4프레임 IDLE)
패턴 시스템으로 풍부한 전투감 구현:

  Phase 1 (HP 100~50%)
  ┌─ WANDER   : 느린 배회, 플레이어 조준 단발 반복
  ├─ CHARGE   : 빨간 전조 후 돌진 (벽에 막히면 경직)
  └─ CROSSFIRE: 십자+대각 탄막 두 번 연속

  Phase 2 (HP 50%~0%)
  ┌─ 위 3가지 패턴 강화
  ├─ SPIRAL   : 회전 탄막 (180°)
  └─ TELEPORT : 페이드 → 플레이어 근처 재등장 → 즉시 전방위 버스트

시각 효과 (스프라이트 변환으로 구현):
  - CHARGE 전조: 빨간 glow + 스케일 업
  - SPIRAL: 천천히 회전
  - TELEPORT: 알파 페이드 인/아웃
  - 피격: 흰 플래시
  - Phase 2: 상시 보라색 오라
"""

import pygame, math, random, base64, heapq
from io import BytesIO
from scripts.bullet    import EnemyBullet
from scripts.animation import Animation

# ── 공통 상수 ──────────────────────────────────────────────
TILE      = 32
DRAW_SIZE = 72   # Phase 2 에서 스케일로 커 보이게


# ══════════════════════════════════════════════════════════
#  A* / LOS (enemy.py 독립 복사)
# ══════════════════════════════════════════════════════════

def _build_wall_set(walls):
    blocked = set()
    for w in walls:
        for ty in range(w.top // TILE, (w.bottom - 1) // TILE + 1):
            for tx in range(w.left // TILE, (w.right - 1) // TILE + 1):
                blocked.add((tx, ty))
    return blocked


def _astar(sx_px, sy_px, gx_px, gy_px, wall_set):
    sx, sy = sx_px // TILE, sy_px // TILE
    gx, gy = gx_px // TILE, gy_px // TILE
    if (sx, sy) == (gx, gy):
        return []

    DIRS = [(1,0,1.0),(-1,0,1.0),(0,1,1.0),(0,-1,1.0),
            (1,1,1.414),(-1,1,1.414),(1,-1,1.414),(-1,-1,1.414)]

    heap = [(abs(gx-sx)+abs(gy-sy), 0.0, sx, sy)]
    came = {}
    g_sc = {(sx, sy): 0.0}

    for _ in range(600):
        if not heap: break
        _, g, cx, cy = heapq.heappop(heap)
        if (cx, cy) == (gx, gy):
            path, node = [], (cx, cy)
            while node in came:
                path.append(node); node = came[node]
            path.reverse()
            return [(tx*TILE+TILE//2, ty*TILE+TILE//2) for tx, ty in path]
        for ddx, ddy, cost in DIRS:
            nx, ny = cx+ddx, cy+ddy
            if (nx, ny) in wall_set: continue
            ng = g + cost
            if ng < g_sc.get((nx, ny), float('inf')):
                g_sc[(nx, ny)] = ng
                came[(nx, ny)] = (cx, cy)
                heapq.heappush(heap, (ng + abs(gx-nx)+abs(gy-ny), ng, nx, ny))
    return []


def _check_los(ax, ay, bx, by, wall_set):
    sx, sy = int(ax)//TILE, int(ay)//TILE
    gx, gy = int(bx)//TILE, int(by)//TILE
    dx, dy = abs(gx-sx), abs(gy-sy)
    xs, ys = (1 if gx > sx else -1), (1 if gy > sy else -1)
    cx, cy, err = sx, sy, dx - dy
    for _ in range(dx+dy+2):
        if (cx, cy) in wall_set: return False
        if (cx, cy) == (gx, gy):  return True
        e2 = err*2
        if e2 > -dy: err -= dy; cx += xs
        if e2 <  dx: err += dx; cy += ys
    return True


# ══════════════════════════════════════════════════════════
#  스프라이트 (절차적 4프레임)
# ══════════════════════════════════════════════════════════

def _make_boss_frames(size=DRAW_SIZE):
    frames = []
    for fi in range(4):
        bob   = [0, -2, -3, -2][fi]
        pulse = [0,  1,  2,  1][fi]
        surf  = pygame.Surface((size, size), pygame.SRCALPHA)
        cx    = size // 2
        cy    = size // 2 + 2 + bob

        # 그림자
        pygame.draw.ellipse(surf, (0, 0, 0, 45),
                            (cx-20, size-12, 40, 11))

        # 망토 (아래쪽으로 넓게)
        robe = [
            (cx-18, cy+18), (cx-22, cy+26), (cx-12, cy+28),
            (cx,    cy+24), (cx+12, cy+28), (cx+22, cy+26),
            (cx+18, cy+18), (cx+13, cy+2),
            (cx,    cy-5),  (cx-13, cy+2),
        ]
        pygame.draw.polygon(surf, (30, 12, 50), robe)
        pygame.draw.polygon(surf, (75, 32, 110), robe, 2)

        # 망토 무늬선
        for dy2 in [8, 16]:
            t = 1 - dy2/28
            pw = int(t * 18)
            pygame.draw.line(surf, (55, 22, 85),
                             (cx-pw, cy+dy2), (cx+pw, cy+dy2), 1)

        # 머리
        pygame.draw.circle(surf, (25, 10, 42), (cx, cy-12), 16)
        pygame.draw.circle(surf, (68, 26, 98), (cx, cy-12), 16, 2)

        # 뿔
        for s in [-1, 1]:
            hx = cx + s*10
            pts = [(hx-3, cy-26), (hx+3, cy-26), (hx+s*2, cy-36)]
            pygame.draw.polygon(surf, (92, 38, 135), pts)
            pygame.draw.polygon(surf, (130, 60, 180), pts, 1)

        # 눈 (빨간 발광)
        er = 195 + pulse * 25
        for ex in [cx-6, cx+6]:
            pygame.draw.circle(surf, (er, 0, 0),       (ex, cy-13), 4)
            pygame.draw.circle(surf, (255, 100, 100),   (ex, cy-13), 2)
            pygame.draw.circle(surf, (255, 200, 200),   (ex, cy-13), 1)

        # 손 (보석 오브)
        for s in [-1, 1]:
            hx = cx + s*(18 + pulse)
            hy = cy + 4
            pygame.draw.circle(surf, (50, 18, 80),     (hx, hy), 7)
            pygame.draw.circle(surf, (135, 55, 210),   (hx, hy), 4)
            pygame.draw.circle(surf, (185, 105, 255),  (hx, hy), 2)
            # 보석 광택
            pygame.draw.circle(surf, (220, 180, 255),  (hx-1, hy-1), 1)

        frames.append(surf)
    return frames


# ══════════════════════════════════════════════════════════
#  Boss 클래스
# ══════════════════════════════════════════════════════════

# 패턴 상수
PAT_WANDER    = "WANDER"
PAT_CHARGE_W  = "CHARGE_WIND"   # 전조 (빨간 glow)
PAT_CHARGE_R  = "CHARGE_RUSH"   # 돌진
PAT_CROSS_1   = "CROSS1"        # 십자 탄막
PAT_CROSS_2   = "CROSS2"        # 대각 탄막 (CROSS1 직후)
PAT_SPIRAL    = "SPIRAL"        # 회전 탄막
PAT_TELE_OUT  = "TELE_OUT"      # 페이드아웃
PAT_TELE_IN   = "TELE_IN"       # 재등장


class Boss:
    NAME   = "Dark Lich"
    MAX_HP = 500
    RADIUS = 24

    _frames_cache = None

    def __init__(self, x, y):
        self.x      = float(x)
        self.y      = float(y)
        self.hp     = self.MAX_HP
        self.alive  = True
        self.flip   = False
        self.score  = 200
        self.phase  = 1

        # 시각 효과용
        self._wobble     = 0.0
        self._rot_angle  = 0.0   # SPIRAL 회전각
        self._alpha      = 255   # TELEPORT 알파
        self._scale      = 1.0   # CHARGE 스케일
        self._hit_timer  = 0

        # 패턴 상태기
        self._pattern     = PAT_WANDER
        self._pat_timer   = random.randint(60, 100)  # 첫 패턴 전 대기
        self._shoot_timer = random.randint(30, 60)
        self._spiral_angle = 0.0   # 스파이럴 현재 각도
        self._charge_dx    = 0.0
        self._charge_dy    = 0.0
        self._tele_target  = (x, y)

        # 경로 탐색
        self._path        = []
        self._path_timer  = 20
        self._wall_set    = None
        self._wall_set_id = None
        self._has_los     = False

        # 애니메이션
        if Boss._frames_cache is None:
            Boss._frames_cache = _make_boss_frames()
        self._anim = Animation(Boss._frames_cache, 8, loop=True)

    # ── 경로 탐색 ────────────────────────────────────────

    def _get_wall_set(self, walls):
        wid = id(walls)
        if wid != self._wall_set_id:
            self._wall_set    = _build_wall_set(walls)
            self._wall_set_id = wid
        return self._wall_set

    def _refresh_path(self, px, py, walls):
        ws = self._get_wall_set(walls)
        self._has_los = _check_los(self.x, self.y, px, py, ws)
        if self._has_los:
            self._path = []
        else:
            self._path = _astar(int(self.x), int(self.y), int(px), int(py), ws)

    def activate(self, px, py, walls):
        self._path_timer = 20
        self._refresh_path(px, py, walls)

    def _desired_dir(self, px, py):
        if self._has_los:
            dx, dy = px - self.x, py - self.y
            d = math.hypot(dx, dy)
            return (dx/d, dy/d) if d > 0 else (0.0, 0.0)
        if not self._path:
            dx, dy = px - self.x, py - self.y
            d = math.hypot(dx, dy)
            return (dx/d, dy/d) if d > 0 else (0.0, 0.0)
        wx, wy = self._path[0]
        d = math.hypot(wx-self.x, wy-self.y)
        if d < TILE * 0.6:
            self._path.pop(0)
            if not self._path: return 0.0, 0.0
            wx, wy = self._path[0]
            d = math.hypot(wx-self.x, wy-self.y)
        return ((wx-self.x)/d, (wy-self.y)/d) if d > 0 else (0.0, 0.0)

    # ── 이동 ────────────────────────────────────────────

    def _move(self, dx, dy, walls):
        r = self.RADIUS
        for axis_dx, axis_dy in [(dx, 0), (0, dy)]:
            if axis_dx == 0 and axis_dy == 0: continue
            self.x += axis_dx
            self.y += axis_dy
            rect = pygame.Rect(int(self.x)-r, int(self.y)-r, r*2, r*2)
            for w in walls:
                if rect.colliderect(w):
                    if axis_dx > 0: self.x = w.left  - r
                    if axis_dx < 0: self.x = w.right + r
                    if axis_dy > 0: self.y = w.top   - r
                    if axis_dy < 0: self.y = w.bottom + r

    # ── 탄 생성 헬퍼 ────────────────────────────────────

    def _bullet(self, angle, speed=4.5, damage=None, color=None):
        dmg = damage or (10 if self.phase == 1 else 14)
        col = color or (255, 80, 80)
        b   = EnemyBullet(self.x, self.y, angle, speed, dmg)
        b.color = col
        return b

    def _burst(self, n, base_angle=None, speed=4.5, damage=None, offset=0.0):
        """n방향 방사. base_angle=None 이면 균등 분배(전방위)."""
        bullets = []
        if base_angle is None:
            for i in range(n):
                bullets.append(self._bullet(2*math.pi/n*i + offset, speed, damage))
        else:
            for i in range(n):
                bullets.append(self._bullet(base_angle + (2*math.pi/n)*i + offset, speed, damage))
        return bullets

    # ── 패턴 선택 ────────────────────────────────────────

    def _pick_next_pattern(self):
        if self.phase == 1:
            return random.choice([
                PAT_WANDER,
                PAT_CHARGE_W,
                PAT_CROSS_1,
                PAT_WANDER,
            ])
        else:
            return random.choice([
                PAT_WANDER,
                PAT_CHARGE_W,
                PAT_CROSS_1,
                PAT_SPIRAL,
                PAT_TELE_OUT,
            ])

    # ── 메인 업데이트 ────────────────────────────────────

    def update(self, player, walls, room_rect=None):
        """반환값: 발사된 EnemyBullet 리스트"""
        if room_rect is not None:
            self._room_rect = room_rect
        if not self.alive:
            return []

        self._wobble    += 0.055
        self._hit_timer  = max(0, self._hit_timer - 1)
        self._path_timer += 1

        px, py = player.x, player.y
        dist   = math.hypot(px-self.x, py-self.y)
        self.flip = (px < self.x)

        # 페이즈 전환
        new_phase = 2 if self.hp <= self.MAX_HP * 0.5 else 1
        if new_phase != self.phase:
            self.phase = new_phase
            self._path_timer = 20

        # 경로 갱신
        if self._path_timer >= 15:
            self._path_timer = 0
            self._refresh_path(px, py, walls)

        bullets = []
        self._pat_timer -= 1

        # ════════════════════════════════════════════════
        #  패턴 처리
        # ════════════════════════════════════════════════

        # ── WANDER ──────────────────────────────────────
        if self._pattern == PAT_WANDER:
            spd = 1.4 if self.phase == 1 else 2.0
            if dist > 90:
                nx, ny = self._desired_dir(px, py)
                self._move(nx * spd, ny * spd, walls)

            self._shoot_timer -= 1
            shoot_cd = 70 if self.phase == 1 else 45
            if self._shoot_timer <= 0:
                self._shoot_timer = shoot_cd
                angle = math.atan2(py-self.y, px-self.x)
                # Phase 1: 조준 2발 V자, Phase 2: 조준 3발 부채꼴
                spread = 0.22
                n_shots = 2 if self.phase == 1 else 3
                for i in range(n_shots):
                    off = (i - (n_shots-1)/2) * spread
                    bullets.append(self._bullet(angle + off))

            self._scale = max(1.0, self._scale - 0.04)

            if self._pat_timer <= 0:
                self._pattern   = self._pick_next_pattern()
                self._pat_timer = random.randint(80, 140)
                self._shoot_timer = max(self._shoot_timer, 20)

        # ── CHARGE_WIND (전조) ───────────────────────────
        elif self._pattern == PAT_CHARGE_W:
            wind_dur = 50
            progress = 1.0 - max(0, self._pat_timer) / wind_dur
            # 스케일 점점 커짐 (1.0 → 1.25)
            self._scale = 1.0 + progress * 0.25
            # 제자리 진동 (작은 흔들림)
            jitter = int(math.sin(self._wobble * 4) * progress * 3)
            self._move(jitter, 0, walls)

            if self._pat_timer <= 0:
                # 돌진 방향 결정
                angle = math.atan2(py-self.y, px-self.x)
                spd   = 9.0 if self.phase == 1 else 13.0
                self._charge_dx = math.cos(angle) * spd
                self._charge_dy = math.sin(angle) * spd
                self._pattern   = PAT_CHARGE_R
                self._pat_timer = 22   # 돌진 지속 시간

        # ── CHARGE_RUSH (돌진) ────────────────────────────
        elif self._pattern == PAT_CHARGE_R:
            self._move(self._charge_dx, self._charge_dy, walls)
            self._scale = max(1.0, self._scale - 0.01)

            if self._pat_timer <= 0:
                # 돌진 종료 → 짧은 경직 후 WANDER
                bullets += self._burst(
                    6 if self.phase == 1 else 10,
                    damage=8
                )
                self._pattern   = PAT_WANDER
                self._pat_timer = random.randint(60, 100)
                self._scale     = 1.0

        # ── CROSS1 (십자 탄막) ────────────────────────────
        elif self._pattern == PAT_CROSS_1:
            if self._pat_timer == 38:
                bullets += self._burst(4, offset=0.0, speed=5.0)
            if self._pat_timer <= 0:
                self._pattern   = PAT_CROSS_2
                self._pat_timer = 28

        # ── CROSS2 (대각 탄막, 즉시) ─────────────────────
        elif self._pattern == PAT_CROSS_2:
            if self._pat_timer == 26:
                bullets += self._burst(4, offset=math.pi/4, speed=5.0)
            if self._pat_timer <= 0:
                self._pattern   = PAT_WANDER
                self._pat_timer = random.randint(60, 100)

        # ── SPIRAL (phase 2 전용) ─────────────────────────
        elif self._pattern == PAT_SPIRAL:
            # 매 4프레임마다 2발씩 나선형 발사
            if self._pat_timer % 3 == 0:
                self._spiral_angle += 0.28
                bullets.append(self._bullet(self._spiral_angle,       speed=3.8, color=(255, 100, 200)))
                bullets.append(self._bullet(self._spiral_angle + math.pi, speed=3.8, color=(255, 100, 200)))

            if self._pat_timer <= 0:
                self._pattern   = PAT_WANDER
                self._pat_timer = random.randint(50, 90)

        # ── TELE_OUT (페이드 아웃) ───────────────────────
        elif self._pattern == PAT_TELE_OUT:
            self._alpha = max(0, int(255 * (self._pat_timer / 35)))
            if self._pat_timer <= 0:
                # 플레이어 근처 빈 곳에 재등장
                angle      = random.uniform(0, math.pi * 2)
                dist_tele  = random.randint(100, 180)
                self.x     = px + math.cos(angle) * dist_tele
                self.y     = py + math.sin(angle) * dist_tele
                self._tele_target = (px, py)
                self._pattern   = PAT_TELE_IN
                self._pat_timer = 30

        # ── TELE_IN (페이드 인 + 즉시 버스트) ───────────
        elif self._pattern == PAT_TELE_IN:
            self._alpha = min(255, int(255 * (1.0 - self._pat_timer / 30)))
            if self._pat_timer == 15:
                # 재등장 순간 전방위 버스트
                bullets += self._burst(12, speed=4.0, damage=10,
                                       color=(200, 80, 255))
            if self._pat_timer <= 0:
                self._alpha   = 255
                self._pattern = PAT_WANDER
                self._pat_timer = random.randint(60, 90)

        # 애니메이션
        self._anim.update()
        return bullets

    # ── 피격 ─────────────────────────────────────────────

    def take_damage(self, amount):
        if not self.alive: return
        self.hp -= amount
        self._hit_timer  = 14
        self._path_timer = 20
        if self.hp <= 0:
            self.hp    = 0
            self.alive = False

    def get_rect(self):
        r = self.RADIUS
        return pygame.Rect(int(self.x)-r, int(self.y)-r, r*2, r*2)

    def is_dead(self):
        return not self.alive

    # ── 그리기 ───────────────────────────────────────────

    def draw(self, screen, cam_x, cam_y):
        if not self.alive:
            return

        sx = int(self.x) - cam_x
        sy = int(self.y) - cam_y

        # ── Phase 2 상시 오라 ──
        if self.phase == 2:
            pulse = int(abs(math.sin(self._wobble)) * 20)
            aura  = pygame.Surface((DRAW_SIZE+28, DRAW_SIZE+28), pygame.SRCALPHA)
            pygame.draw.circle(aura, (100, 0, 190, 28+pulse),
                               ((DRAW_SIZE+28)//2, (DRAW_SIZE+28)//2),
                               DRAW_SIZE//2+10)
            screen.blit(aura, (sx - (DRAW_SIZE+28)//2, sy - (DRAW_SIZE+28)//2))

        # ── CHARGE 전조 glow ──
        if self._pattern == PAT_CHARGE_W:
            glow_r = int(self._scale * DRAW_SIZE // 2 + 12)
            glow   = pygame.Surface((glow_r*2+4, glow_r*2+4), pygame.SRCALPHA)
            alpha  = int(max(0, min(200, (1.0 - self._pat_timer/50) * 220)))
            pygame.draw.circle(glow, (255, 40, 40, alpha),
                               (glow_r+2, glow_r+2), glow_r)
            screen.blit(glow, (sx - glow_r - 2, sy - glow_r - 2))

        # ── TELEPORT 알파 적용 ──
        use_alpha = self._alpha if self._pattern in (PAT_TELE_OUT, PAT_TELE_IN) else 255

        # ── 스프라이트 가져오기 ──
        img = self._anim.get_image().copy()

        # 피격 플래시
        if self._hit_timer > 0 and (self._hit_timer // 3) % 2 == 0:
            flash = pygame.Surface((DRAW_SIZE, DRAW_SIZE), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 160))
            img.blit(flash, (0, 0))

        # 스케일 변환
        if abs(self._scale - 1.0) > 0.02:
            sz  = int(DRAW_SIZE * self._scale)
            img = pygame.transform.scale(img, (sz, sz))
        else:
            sz  = DRAW_SIZE

        # 좌우 반전
        if self.flip:
            img = pygame.transform.flip(img, True, False)

        # 알파 적용 (TELEPORT)
        if use_alpha < 255:
            img = img.copy()
            img.set_alpha(use_alpha)

        screen.blit(img, (sx - sz//2, sy - sz//2))

        # ── CHARGE_W 전조 경고 원 ──
        if self._pattern == PAT_CHARGE_W and self._pat_timer < 35:
            warn_r = int(self.RADIUS * 2.5 * (1 - self._pat_timer/35))
            if warn_r > 0:
                surf = pygame.Surface((warn_r*2, warn_r*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 80, 0, 80),
                                   (warn_r, warn_r), warn_r)
                screen.blit(surf, (sx - warn_r, sy - warn_r))

    # ── 보스 HP바 ────────────────────────────────────────

    def draw_boss_bar(self, screen, sw):
        bw, bh = 360, 20
        bx = sw//2 - bw//2
        by = 10

        # 배경
        panel = pygame.Surface((bw+20, bh+24), pygame.SRCALPHA)
        pygame.draw.rect(panel, (15, 5, 30, 210), (0, 0, bw+20, bh+24), border_radius=8)
        pygame.draw.rect(panel, (100, 30, 160, 180), (0, 0, bw+20, bh+24), 2, border_radius=8)
        screen.blit(panel, (bx-10, by-4))

        # HP 바
        pygame.draw.rect(screen, (50, 15, 55), (bx, by+8, bw, bh-4), border_radius=4)
        ratio = max(self.hp / self.MAX_HP, 0)
        if self.phase == 1:
            bar_col = (170, 35, 215)
        else:
            pulse   = int(abs(math.sin(self._wobble * 1.5)) * 28)
            bar_col = (195 + pulse//4, 18, 75)
        if ratio > 0:
            pygame.draw.rect(screen, bar_col,
                             (bx, by+8, int(bw*ratio), bh-4), border_radius=4)
        pygame.draw.rect(screen, (200, 120, 255),
                         (bx, by+8, bw, bh-4), 2, border_radius=4)

        # HP 50% 경계선
        pygame.draw.line(screen, (255, 200, 60),
                         (bx + bw//2, by+6), (bx + bw//2, by+bh+4), 1)

        font     = pygame.font.SysFont(None, 22)
        name_col = (220, 150, 255) if self.phase == 1 else (255, 100, 100)
        nt       = font.render(self.NAME, True, name_col)
        screen.blit(nt, (bx, by - 1))

        # 패턴 표시 (디버그 겸 연출)
        pat_names = {
            PAT_WANDER:   "...",
            PAT_CHARGE_W: "!! CHARGE !!",
            PAT_CHARGE_R: "→→→",
            PAT_CROSS_1:  "✦ CROSS",
            PAT_CROSS_2:  "✦ CROSS",
            PAT_SPIRAL:   "↻ SPIRAL",
            PAT_TELE_OUT: "~ TELEPORT ~",
            PAT_TELE_IN:  "~ TELEPORT ~",
        }
        ph_col = (160, 80, 255) if self.phase == 1 else (255, 60, 60)
        pt_txt = f"Phase {self.phase}  {pat_names.get(self._pattern,'')}"
        pt     = font.render(pt_txt, True, ph_col)
        screen.blit(pt, (bx + bw - pt.get_width(), by - 1))


# ══════════════════════════════════════════════════════════
#  공통 유틸: 안전 순간이동 (Boss 에 추가)
# ══════════════════════════════════════════════════════════

def _safe_teleport(boss, px, py, walls, room_rect=None):
    """방 경계 + 벽 충돌 검사로 안전한 위치에 순간이동."""
    r      = boss.RADIUS
    margin = r + 8
    if room_rect is not None:
        rx, ry = room_rect.left + margin, room_rect.top + margin
        rr, rb = room_rect.right - margin, room_rect.bottom - margin
    else:
        rx, ry, rr, rb = px-400, py-400, px+400, py+400
    for _ in range(25):
        angle = random.uniform(0, math.pi * 2)
        dist  = random.randint(100, 200)
        nx    = max(rx, min(rr, px + math.cos(angle) * dist))
        ny    = max(ry, min(rb, py + math.sin(angle) * dist))
        tr    = pygame.Rect(int(nx)-r, int(ny)-r, r*2, r*2)
        if not any(tr.colliderect(w) for w in walls):
            boss.x, boss.y = float(nx), float(ny)
            return
    boss.x, boss.y = float(nx), float(ny)   # fallback


# ══════════════════════════════════════════════════════════
#  Boss 2 – Iron Golem  (2층)
#  ▸ 두꺼운 장갑, 느리지만 강함
#  STOMP  : 경고원 → 충격파 링 탄막
#  GATLING: 빠른 부채꼴 연발
#  SHIELD : 일시 무적 (반격 아님)
#  SLAM   : Phase2 – 플레이어 방향 돌진 + 착탄 폭발
# ══════════════════════════════════════════════════════════

B2_IDLE    = "B2_IDLE"
B2_STOMP   = "B2_STOMP"
B2_GATLING = "B2_GATLING"
B2_SHIELD  = "B2_SHIELD"
B2_SLAM_W  = "B2_SLAM_W"
B2_SLAM_R  = "B2_SLAM_R"


def _make_golem_frames(size=80):
    frames = []
    for fi in range(4):
        bob  = [0, -1, -2, -1][fi]
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size//2, size//2 + bob

        # 몸통 (육각형 느낌)
        body = [
            (cx-20, cy-28), (cx+20, cy-28),
            (cx+28, cy-10), (cx+28, cy+18),
            (cx+16, cy+30), (cx-16, cy+30),
            (cx-28, cy+18), (cx-28, cy-10),
        ]
        pygame.draw.polygon(surf, (80, 85, 90), body)
        pygame.draw.polygon(surf, (130, 140, 150), body, 3)

        # 코어 (가슴 중앙 주황 보석)
        pulse = [0,1,2,1][fi]
        pygame.draw.circle(surf, (60, 30, 0), (cx, cy), 10)
        pygame.draw.circle(surf, (255, 140 + pulse*20, 0), (cx, cy), 7)
        pygame.draw.circle(surf, (255, 220, 100), (cx, cy), 3)

        # 눈 (빨간)
        for ex in [cx-8, cx+8]:
            pygame.draw.circle(surf, (200, 0, 0), (ex, cy-14), 4)
            pygame.draw.circle(surf, (255, 80, 80), (ex, cy-14), 2)

        # 팔 (굵고 짧음)
        for s in [-1, 1]:
            ax = cx + s*30
            pygame.draw.rect(surf, (70, 75, 80),
                             (ax - 6, cy - 8, 12, 24))
            pygame.draw.rect(surf, (110, 120, 130),
                             (ax - 6, cy - 8, 12, 24), 2)

        frames.append(surf)
    return frames


class Boss2(Boss):
    NAME   = "Iron Golem"
    MAX_HP = 800
    RADIUS = 28
    _frames_cache = None

    def __init__(self, x, y):
        super().__init__(x, y)
        if Boss2._frames_cache is None:
            Boss2._frames_cache = _make_golem_frames()
        self._anim      = Animation(Boss2._frames_cache, 8, loop=True)
        self._pattern   = B2_IDLE
        self._pat_timer = random.randint(60, 100)
        self._shield_on = False
        self._stomp_warned = False
        self._room_rect    = None
        self.score = 350

    def _pick_next(self):
        if self.phase == 1:
            return random.choice([B2_IDLE, B2_STOMP, B2_GATLING, B2_SHIELD])
        return random.choice([B2_IDLE, B2_STOMP, B2_GATLING, B2_SLAM_W])

    def take_damage(self, amount):
        if self._shield_on: return
        super().take_damage(amount)

    def update(self, player, walls, room_rect=None):
        if not self.alive: return []
        if room_rect: self._room_rect = room_rect
        self._wobble   += 0.04
        self._hit_timer = max(0, self._hit_timer - 1)
        self._path_timer += 1
        px, py = player.x, player.y
        self.flip = (px < self.x)
        new_phase = 2 if self.hp <= self.MAX_HP * 0.5 else 1
        if new_phase != self.phase: self.phase = new_phase
        if self._path_timer >= 20:
            self._path_timer = 0
            self._refresh_path(px, py, walls)
        bullets = []
        self._pat_timer -= 1

        # IDLE – 느리게 접근하며 단발
        if self._pattern == B2_IDLE:
            spd = 1.0 if self.phase == 1 else 1.5
            if math.hypot(px-self.x, py-self.y) > 80:
                nx, ny = self._desired_dir(px, py)
                self._move(nx*spd, ny*spd, walls)
            self._shoot_timer -= 1
            if self._shoot_timer <= 0:
                self._shoot_timer = 80
                angle = math.atan2(py-self.y, px-self.x)
                bullets.append(self._bullet(angle, speed=3.5, damage=12))
            if self._pat_timer <= 0:
                self._pattern   = self._pick_next()
                self._pat_timer = random.randint(80, 120)

        # STOMP – 제자리, 경고원 → 충격파 링
        elif self._pattern == B2_STOMP:
            if self._pat_timer == 55 and not self._stomp_warned:
                self._stomp_warned = True
            if self._pat_timer == 30:
                n = 12 if self.phase == 1 else 18
                bullets += self._burst(n, speed=4.0, damage=14)
                if self.phase == 2:
                    bullets += self._burst(n, speed=6.5, damage=10, offset=math.pi/n)
            if self._pat_timer <= 0:
                self._stomp_warned = False
                self._pattern   = self._pick_next()
                self._pat_timer = random.randint(80, 110)

        # GATLING – 부채꼴 빠른 연발
        elif self._pattern == B2_GATLING:
            angle = math.atan2(py-self.y, px-self.x)
            cd = 4 if self.phase == 1 else 3
            if self._pat_timer % cd == 0:
                spread = 0.35
                n = 3 if self.phase == 1 else 5
                for i in range(n):
                    off = (i-(n-1)/2)*spread
                    bullets.append(self._bullet(angle+off, speed=5.5, damage=8))
            if self._pat_timer <= 0:
                self._pattern   = self._pick_next()
                self._pat_timer = random.randint(70, 100)

        # SHIELD – 무적 (공격 안 함)
        elif self._pattern == B2_SHIELD:
            self._shield_on = True
            if self._pat_timer <= 0:
                self._shield_on = False
                self._pattern   = self._pick_next()
                self._pat_timer = random.randint(80, 120)

        # SLAM_W – 전조
        elif self._pattern == B2_SLAM_W:
            self._scale = 1.0 + (1.0 - max(0,self._pat_timer)/40) * 0.3
            if self._pat_timer <= 0:
                angle = math.atan2(py-self.y, px-self.x)
                self._charge_dx = math.cos(angle)*11
                self._charge_dy = math.sin(angle)*11
                self._pattern   = B2_SLAM_R
                self._pat_timer = 20

        # SLAM_R – 돌진 + 착탄 폭발
        elif self._pattern == B2_SLAM_R:
            self._move(self._charge_dx, self._charge_dy, walls)
            self._scale = max(1.0, self._scale-0.02)
            if self._pat_timer <= 0:
                bullets += self._burst(16, speed=4.5, damage=12)
                self._pattern   = self._pick_next()
                self._pat_timer = random.randint(70,100)
                self._scale     = 1.0

        self._anim.update()
        return bullets

    def draw(self, screen, cam_x, cam_y):
        if not self.alive: return
        sx = int(self.x)-cam_x
        sy = int(self.y)-cam_y
        # STOMP 경고원
        if self._pattern == B2_STOMP and self._stomp_warned:
            warn_r = 60 + int(abs(math.sin(self._wobble*3))*10)
            ws = pygame.Surface((warn_r*2, warn_r*2), pygame.SRCALPHA)
            pygame.draw.circle(ws, (255,120,0,50),(warn_r,warn_r),warn_r)
            pygame.draw.circle(ws, (255,180,0,120),(warn_r,warn_r),warn_r,2)
            screen.blit(ws,(sx-warn_r, sy-warn_r))
        # 실드 오라
        if self._shield_on:
            pulse = int(abs(math.sin(self._wobble*2))*30)
            sa = pygame.Surface((80,80), pygame.SRCALPHA)
            pygame.draw.circle(sa,(100,200,255,80+pulse),(40,40),36)
            pygame.draw.circle(sa,(180,240,255,200),(40,40),36,3)
            screen.blit(sa,(sx-40,sy-40))
        # SLAM 전조 glow
        if self._pattern == B2_SLAM_W:
            gw = pygame.Surface((100,100),pygame.SRCALPHA)
            a  = int((self._scale-1.0)/0.3*180)
            pygame.draw.circle(gw,(255,80,0,a),(50,50),44)
            screen.blit(gw,(sx-50,sy-50))
        img = self._anim.get_image().copy()
        if self._hit_timer > 0 and (self._hit_timer//3)%2==0:
            fl = pygame.Surface((80,80),pygame.SRCALPHA); fl.fill((255,255,255,160)); img.blit(fl,(0,0))
        sz = 80
        if abs(self._scale-1.0)>0.02:
            sz=int(80*self._scale); img=pygame.transform.scale(img,(sz,sz))
        if self.flip: img=pygame.transform.flip(img,True,False)
        screen.blit(img,(sx-sz//2,sy-sz//2))

    def draw_boss_bar(self, screen, sw):
        bw,bh=360,20; bx=sw//2-bw//2; by=10
        panel=pygame.Surface((bw+20,bh+24),pygame.SRCALPHA)
        pygame.draw.rect(panel,(20,20,20,210),(0,0,bw+20,bh+24),border_radius=8)
        pygame.draw.rect(panel,(140,140,160,180),(0,0,bw+20,bh+24),2,border_radius=8)
        screen.blit(panel,(bx-10,by-4))
        pygame.draw.rect(screen,(40,40,40),(bx,by+8,bw,bh-4),border_radius=4)
        ratio=max(self.hp/self.MAX_HP,0)
        bc=(100,140,180) if self.phase==1 else (200,120,30)
        if self._shield_on: bc=(120,220,255)
        if ratio>0: pygame.draw.rect(screen,bc,(bx,by+8,int(bw*ratio),bh-4),border_radius=4)
        pygame.draw.rect(screen,(180,200,220),(bx,by+8,bw,bh-4),2,border_radius=4)
        pygame.draw.line(screen,(255,200,60),(bx+bw//2,by+6),(bx+bw//2,by+bh+4),1)
        font=pygame.font.SysFont(None,22)
        nc=(160,180,200) if self.phase==1 else (255,140,40)
        screen.blit(font.render(self.NAME,True,nc),(bx,by-1))
        pat={B2_IDLE:"...",B2_STOMP:"!! STOMP !!",B2_GATLING:">> GATLING",B2_SHIELD:"[ SHIELD ]",B2_SLAM_W:"!! SLAM !!",B2_SLAM_R:">>>"}
        pt=font.render(f"Phase {self.phase}  {pat.get(self._pattern,'')}",True,(160,180,200) if self.phase==1 else (255,140,40))
        screen.blit(pt,(bx+bw-pt.get_width(),by-1))


# ══════════════════════════════════════════════════════════
#  Boss 3 – Phantom Witch  (3층)
#  RAIN  : 하늘에서 탄 낙하 패턴
#  RING  : 확장 탄 링
#  BLINK : 빠른 3연속 순간이동
#  CLONE : 여러 위치에서 동시 사격
# ══════════════════════════════════════════════════════════

B3_IDLE  = "B3_IDLE"
B3_RAIN  = "B3_RAIN"
B3_RING  = "B3_RING"
B3_BLINK = "B3_BLINK"
B3_CLONE = "B3_CLONE"


def _make_witch_frames(size=72):
    frames = []
    for fi in range(4):
        bob  = [0,-3,-5,-3][fi]
        surf = pygame.Surface((size,size),pygame.SRCALPHA)
        cx, cy = size//2, size//2+bob

        # 망토 (보라/남색)
        robe=[
            (cx-14,cy+10),(cx-18,cy+22),(cx-8,cy+26),
            (cx,cy+22),(cx+8,cy+26),(cx+18,cy+22),
            (cx+14,cy+10),(cx+10,cy-2),(cx,cy-6),(cx-10,cy-2),
        ]
        pygame.draw.polygon(surf,(50,20,90),robe)
        pygame.draw.polygon(surf,(120,50,200),robe,2)

        # 머리
        pygame.draw.circle(surf,(40,15,70),(cx,cy-14),13)
        pygame.draw.circle(surf,(100,40,160),(cx,cy-14),13,2)

        # 모자
        hat=[(cx-12,cy-24),(cx+12,cy-24),(cx+8,cy-40),(cx-8,cy-40)]
        pygame.draw.polygon(surf,(25,8,45),hat)
        pygame.draw.polygon(surf,(90,30,140),hat,2)
        pygame.draw.rect(surf,(25,8,45),(cx-14,cy-26,28,5))

        # 눈 (녹색 빛)
        pulse=[0,1,2,1][fi]
        for ex in [cx-5,cx+5]:
            pygame.draw.circle(surf,(0,180+pulse*20,80),(ex,cy-15),3)
            pygame.draw.circle(surf,(100,255,160),(ex,cy-15),1)

        # 마법 오브
        oa=int(abs(math.sin(fi*math.pi/2))*80)
        for s in [-1,1]:
            ox2=cx+s*20; oy2=cy+2
            pygame.draw.circle(surf,(20,10,40),(ox2,oy2),6)
            pygame.draw.circle(surf,(80,0,200),(ox2,oy2),4)
            pygame.draw.circle(surf,(180,100,255),(ox2,oy2),2)
        frames.append(surf)
    return frames


class Boss3(Boss):
    NAME   = "Phantom Witch"
    MAX_HP = 650
    RADIUS = 22
    _frames_cache = None

    def __init__(self, x, y):
        super().__init__(x, y)
        if Boss3._frames_cache is None:
            Boss3._frames_cache = _make_witch_frames()
        self._anim      = Animation(Boss3._frames_cache, 7, loop=True)
        self._pattern   = B3_IDLE
        self._pat_timer = random.randint(50, 90)
        self._blink_count = 0
        self._room_rect   = None
        self._alpha       = 255
        self.score = 400

    def _pick_next(self):
        if self.phase==1:
            return random.choice([B3_IDLE,B3_RAIN,B3_RING,B3_BLINK])
        return random.choice([B3_IDLE,B3_RAIN,B3_RING,B3_BLINK,B3_CLONE])

    def update(self, player, walls, room_rect=None):
        if not self.alive: return []
        if room_rect: self._room_rect = room_rect
        self._wobble   += 0.06
        self._hit_timer = max(0, self._hit_timer-1)
        self._path_timer += 1
        px,py = player.x,player.y
        self.flip = (px < self.x)
        new_phase = 2 if self.hp<=self.MAX_HP*0.5 else 1
        if new_phase!=self.phase: self.phase=new_phase
        if self._path_timer>=15:
            self._path_timer=0
            self._refresh_path(px,py,walls)
        bullets=[]; self._pat_timer-=1

        # IDLE – 천천히 맴돌며 조준 2발
        if self._pattern==B3_IDLE:
            spd=1.2 if self.phase==1 else 1.8
            if math.hypot(px-self.x,py-self.y)>100:
                nx,ny=self._desired_dir(px,py)
                self._move(nx*spd,ny*spd,walls)
            self._shoot_timer-=1
            if self._shoot_timer<=0:
                self._shoot_timer=55 if self.phase==1 else 38
                a=math.atan2(py-self.y,px-self.x)
                for off in [-0.18,0.18]:
                    bullets.append(self._bullet(a+off,speed=4.2,damage=10,color=(180,80,255)))
            if self._pat_timer<=0:
                self._pattern=self._pick_next()
                self._pat_timer=random.randint(70,110)

        # RAIN – 플레이어 주변에 탄 낙하
        elif self._pattern==B3_RAIN:
            interval=6 if self.phase==1 else 4
            if self._pat_timer%interval==0:
                for _ in range(2 if self.phase==1 else 3):
                    ox=random.randint(-80,80); oy=random.randint(-80,80)
                    tx,ty=px+ox,py+oy
                    a=math.atan2(ty-self.y,tx-self.x)
                    bullets.append(self._bullet(a,speed=4.5,damage=11,color=(150,0,255)))
            if self._pat_timer<=0:
                self._pattern=self._pick_next()
                self._pat_timer=random.randint(70,100)

        # RING – 여러 겹의 확장 링 탄막
        elif self._pattern==B3_RING:
            rings=[(50,8,4.0),(30,12,5.5)] if self.phase==2 else [(40,8,4.0)]
            for trigger,n,spd in rings:
                if self._pat_timer==trigger:
                    bullets+=self._burst(n,speed=spd,damage=10,color=(100,50,255))
            if self._pat_timer<=0:
                self._pattern=self._pick_next()
                self._pat_timer=random.randint(70,100)

        # BLINK – 연속 순간이동 후 버스트
        elif self._pattern==B3_BLINK:
            if self._pat_timer in [55,40,25]:
                _safe_teleport(self,px,py,walls,self._room_rect)
                self._alpha=0
            # 페이드 인
            if self._alpha<255: self._alpha=min(255,self._alpha+20)
            if self._pat_timer==10:
                n=10 if self.phase==1 else 16
                bullets+=self._burst(n,speed=3.8,damage=12,color=(200,100,255))
            if self._pat_timer<=0:
                self._alpha=255
                self._pattern=self._pick_next()
                self._pat_timer=random.randint(70,100)

        # CLONE – Phase2: 4방향 가상 위치에서 동시 사격
        elif self._pattern==B3_CLONE:
            if self._pat_timer==40:
                offsets=[(120,0),(-120,0),(0,120),(0,-120)]
                a=math.atan2(py-self.y,px-self.x)
                for ox2,oy2 in offsets:
                    cx2,cy2=self.x+ox2,self.y+oy2
                    a2=math.atan2(py-cy2,px-cx2)
                    b=EnemyBullet(cx2,cy2,a2,speed=4.5,damage=10)
                    b.color=(200,100,255)
                    bullets.append(b)
                bullets+=self._burst(8,speed=4.0,damage=9,color=(150,50,220))
            if self._pat_timer<=0:
                self._pattern=self._pick_next()
                self._pat_timer=random.randint(70,100)

        self._anim.update()
        return bullets

    def draw(self, screen, cam_x, cam_y):
        if not self.alive: return
        sx=int(self.x)-cam_x; sy=int(self.y)-cam_y
        # 상시 마법 오라
        pulse=int(abs(math.sin(self._wobble))*25)
        ao=pygame.Surface((80,80),pygame.SRCALPHA)
        pygame.draw.circle(ao,(120,0,220,30+pulse),(40,40),34)
        screen.blit(ao,(sx-40,sy-40))
        img=self._anim.get_image().copy()
        if self._hit_timer>0 and (self._hit_timer//3)%2==0:
            fl=pygame.Surface((72,72),pygame.SRCALPHA); fl.fill((255,255,255,160)); img.blit(fl,(0,0))
        if self.flip: img=pygame.transform.flip(img,True,False)
        if self._alpha<255: img=img.copy(); img.set_alpha(self._alpha)
        screen.blit(img,(sx-36,sy-36))

    def draw_boss_bar(self, screen, sw):
        bw,bh=360,20; bx=sw//2-bw//2; by=10
        p=pygame.Surface((bw+20,bh+24),pygame.SRCALPHA)
        pygame.draw.rect(p,(15,5,30,210),(0,0,bw+20,bh+24),border_radius=8)
        pygame.draw.rect(p,(120,40,200,180),(0,0,bw+20,bh+24),2,border_radius=8)
        screen.blit(p,(bx-10,by-4))
        pygame.draw.rect(screen,(40,10,60),(bx,by+8,bw,bh-4),border_radius=4)
        ratio=max(self.hp/self.MAX_HP,0)
        bc=(120,40,200) if self.phase==1 else (200,60,255)
        if ratio>0: pygame.draw.rect(screen,bc,(bx,by+8,int(bw*ratio),bh-4),border_radius=4)
        pygame.draw.rect(screen,(200,120,255),(bx,by+8,bw,bh-4),2,border_radius=4)
        pygame.draw.line(screen,(255,200,60),(bx+bw//2,by+6),(bx+bw//2,by+bh+4),1)
        font=pygame.font.SysFont(None,22)
        nc=(180,100,255)
        screen.blit(font.render(self.NAME,True,nc),(bx,by-1))
        pat={B3_IDLE:"...",B3_RAIN:"↓ RAIN",B3_RING:"◎ RING",B3_BLINK:"~ BLINK ~",B3_CLONE:"❋ CLONE"}
        pt=font.render(f"Phase {self.phase}  {pat.get(self._pattern,'')}",True,nc)
        screen.blit(pt,(bx+bw-pt.get_width(),by-1))


# ══════════════════════════════════════════════════════════
#  Boss 4 – Thunder Drake  (4층)
#  LIGHTNING : 예고 원 → 번개 탄막 (낙뢰)
#  BARRAGE   : 고속 다방향 연발
#  DASH      : 초고속 돌진 (방향 예측 어려움)
#  THUNDER   : 회전하는 전기 링 2겹
# ══════════════════════════════════════════════════════════

B4_IDLE      = "B4_IDLE"
B4_LIGHTNING = "B4_LIGHTNING"
B4_BARRAGE   = "B4_BARRAGE"
B4_DASH      = "B4_DASH"
B4_THUNDER   = "B4_THUNDER"


def _make_drake_frames(size=80):
    frames=[]
    for fi in range(4):
        bob=[0,-2,-4,-2][fi]
        surf=pygame.Surface((size,size),pygame.SRCALPHA)
        cx,cy=size//2,size//2+bob

        # 날개 (좌우 삼각형)
        for s in [-1,1]:
            wing=[(cx+s*6,cy-8),(cx+s*32,cy-18),(cx+s*28,cy+10)]
            pygame.draw.polygon(surf,(20,60,130),wing)
            pygame.draw.polygon(surf,(60,130,220),wing,2)

        # 몸통 (유선형)
        body=[(cx-10,cy-20),(cx+10,cy-20),(cx+16,cy),(cx+10,cy+20),(cx-10,cy+20),(cx-16,cy)]
        pygame.draw.polygon(surf,(25,70,160),body)
        pygame.draw.polygon(surf,(80,160,255),body,2)

        # 전기 문양
        pulse=[0,1,2,1][fi]
        ec=(180+pulse*20,220,255)
        pygame.draw.line(surf,ec,(cx-6,cy-10),(cx,cy),(2))
        pygame.draw.line(surf,ec,(cx,cy),(cx+6,cy+10),(2))

        # 눈 (노란 전기)
        for ex,ey in [(cx-5,cy-10),(cx+5,cy-10)]:
            pygame.draw.circle(surf,(255,220,0),(ex,ey),4)
            pygame.draw.circle(surf,(255,255,180),(ex,ey),2)

        frames.append(surf)
    return frames


class Boss4(Boss):
    NAME   = "Thunder Drake"
    MAX_HP = 950
    RADIUS = 26
    _frames_cache = None

    def __init__(self, x, y):
        super().__init__(x, y)
        if Boss4._frames_cache is None:
            Boss4._frames_cache = _make_drake_frames()
        self._anim        = Animation(Boss4._frames_cache, 6, loop=True)
        self._pattern     = B4_IDLE
        self._pat_timer   = random.randint(50,90)
        self._thunder_ang = 0.0
        self._lightning_targets = []
        self._room_rect   = None
        self.score = 500

    def _pick_next(self):
        if self.phase==1:
            return random.choice([B4_IDLE,B4_LIGHTNING,B4_BARRAGE,B4_DASH])
        return random.choice([B4_IDLE,B4_LIGHTNING,B4_BARRAGE,B4_DASH,B4_THUNDER])

    def update(self, player, walls, room_rect=None):
        if not self.alive: return []
        if room_rect: self._room_rect=room_rect
        self._wobble+=0.07
        self._hit_timer=max(0,self._hit_timer-1)
        self._path_timer+=1
        px,py=player.x,player.y
        self.flip=(px<self.x)
        new_phase=2 if self.hp<=self.MAX_HP*0.5 else 1
        if new_phase!=self.phase: self.phase=new_phase
        if self._path_timer>=12:
            self._path_timer=0
            self._refresh_path(px,py,walls)
        bullets=[]; self._pat_timer-=1

        # IDLE – 빠르게 접근하며 단발
        if self._pattern==B4_IDLE:
            spd=1.8 if self.phase==1 else 2.5
            if math.hypot(px-self.x,py-self.y)>80:
                nx,ny=self._desired_dir(px,py)
                self._move(nx*spd,ny*spd,walls)
            self._shoot_timer-=1
            if self._shoot_timer<=0:
                self._shoot_timer=50 if self.phase==1 else 35
                a=math.atan2(py-self.y,px-self.x)
                for off in [-0.15,0,0.15]:
                    bullets.append(self._bullet(a+off,speed=5.5,damage=11,color=(100,180,255)))
            if self._pat_timer<=0:
                self._pattern=self._pick_next()
                self._pat_timer=random.randint(70,100)

        # LIGHTNING – 예고 후 낙뢰
        elif self._pattern==B4_LIGHTNING:
            if self._pat_timer==55:
                # 낙뢰 대상 위치 저장
                n=4 if self.phase==1 else 6
                self._lightning_targets=[
                    (px+random.randint(-100,100),py+random.randint(-100,100))
                    for _ in range(n)
                ]
            # 예고원은 draw에서 처리, 실제 낙뢰
            if self._pat_timer==20:
                for tx,ty in self._lightning_targets:
                    a=math.atan2(ty-self.y,tx-self.x)
                    for _ in range(3):
                        a2=a+random.uniform(-0.2,0.2)
                        bullets.append(self._bullet(a2,speed=6.0,damage=14,color=(180,220,255)))
            if self._pat_timer<=0:
                self._lightning_targets=[]
                self._pattern=self._pick_next()
                self._pat_timer=random.randint(70,100)

        # BARRAGE – 고속 다방향 연발
        elif self._pattern==B4_BARRAGE:
            cd=3 if self.phase==1 else 2
            if self._pat_timer%cd==0:
                a=math.atan2(py-self.y,px-self.x)+random.uniform(-0.3,0.3)
                n=4 if self.phase==1 else 6
                bullets+=self._burst(n,base_angle=a,speed=5.8,damage=9)
            if self._pat_timer<=0:
                self._pattern=self._pick_next()
                self._pat_timer=random.randint(60,90)

        # DASH – 초고속 돌진 (2~3회)
        elif self._pattern==B4_DASH:
            if self._pat_timer in [55,38,21] and self.phase==2 or self._pat_timer==50 and self.phase==1:
                angle=math.atan2(py-self.y,px-self.x)
                self._charge_dx=math.cos(angle)*14
                self._charge_dy=math.sin(angle)*14
            if abs(self._charge_dx)>0.1 or abs(self._charge_dy)>0.1:
                self._move(self._charge_dx,self._charge_dy,walls)
                self._charge_dx*=0.85
                self._charge_dy*=0.85
            if self._pat_timer<=0:
                self._charge_dx=self._charge_dy=0.0
                self._pattern=self._pick_next()
                self._pat_timer=random.randint(70,100)

        # THUNDER – 회전 전기 링 2겹 (Phase2)
        elif self._pattern==B4_THUNDER:
            if self._pat_timer%3==0:
                self._thunder_ang+=0.22
                spd1,spd2=4.0,6.0
                bullets.append(self._bullet(self._thunder_ang,speed=spd1,damage=10,color=(100,200,255)))
                bullets.append(self._bullet(self._thunder_ang+math.pi,speed=spd1,damage=10,color=(100,200,255)))
                bullets.append(self._bullet(self._thunder_ang+math.pi/2,speed=spd2,damage=8,color=(200,240,255)))
                bullets.append(self._bullet(self._thunder_ang-math.pi/2,speed=spd2,damage=8,color=(200,240,255)))
            if self._pat_timer<=0:
                self._pattern=self._pick_next()
                self._pat_timer=random.randint(70,100)

        self._anim.update()
        return bullets

    def draw(self, screen, cam_x, cam_y):
        if not self.alive: return
        sx=int(self.x)-cam_x; sy=int(self.y)-cam_y
        # 전기 오라
        pulse=int(abs(math.sin(self._wobble*2))*25)
        ea=pygame.Surface((90,90),pygame.SRCALPHA)
        pygame.draw.circle(ea,(60,160,255,30+pulse),(45,45),38)
        screen.blit(ea,(sx-45,sy-45))
        # 낙뢰 예고원
        for tx,ty in self._lightning_targets:
            tsx,tsy=tx-cam_x,ty-cam_y
            ws=pygame.Surface((60,60),pygame.SRCALPHA)
            a=int(abs(math.sin(self._wobble*4))*150)+50
            pygame.draw.circle(ws,(255,255,100,a),(30,30),28)
            pygame.draw.circle(ws,(255,255,180,200),(30,30),28,2)
            screen.blit(ws,(tsx-30,tsy-30))
        img=self._anim.get_image().copy()
        if self._hit_timer>0 and (self._hit_timer//3)%2==0:
            fl=pygame.Surface((80,80),pygame.SRCALPHA); fl.fill((255,255,255,160)); img.blit(fl,(0,0))
        if self.flip: img=pygame.transform.flip(img,True,False)
        screen.blit(img,(sx-40,sy-40))

    def draw_boss_bar(self, screen, sw):
        bw,bh=360,20; bx=sw//2-bw//2; by=10
        p=pygame.Surface((bw+20,bh+24),pygame.SRCALPHA)
        pygame.draw.rect(p,(5,15,30,210),(0,0,bw+20,bh+24),border_radius=8)
        pygame.draw.rect(p,(60,140,220,180),(0,0,bw+20,bh+24),2,border_radius=8)
        screen.blit(p,(bx-10,by-4))
        pygame.draw.rect(screen,(10,30,60),(bx,by+8,bw,bh-4),border_radius=4)
        ratio=max(self.hp/self.MAX_HP,0)
        bc=(60,140,220) if self.phase==1 else (120,220,255)
        if ratio>0: pygame.draw.rect(screen,bc,(bx,by+8,int(bw*ratio),bh-4),border_radius=4)
        pygame.draw.rect(screen,(140,220,255),(bx,by+8,bw,bh-4),2,border_radius=4)
        pygame.draw.line(screen,(255,200,60),(bx+bw//2,by+6),(bx+bw//2,by+bh+4),1)
        font=pygame.font.SysFont(None,22)
        nc=(100,200,255) if self.phase==1 else (200,240,255)
        screen.blit(font.render(self.NAME,True,nc),(bx,by-1))
        pat={B4_IDLE:"...",B4_LIGHTNING:"⚡ LIGHTNING",B4_BARRAGE:">> BARRAGE",B4_DASH:"→→ DASH",B4_THUNDER:"◎ THUNDER"}
        pt=font.render(f"Phase {self.phase}  {pat.get(self._pattern,'')}",True,nc)
        screen.blit(pt,(bx+bw-pt.get_width(),by-1))


# ══════════════════════════════════════════════════════════
#  Boss 5 – Chaos Lord  (5층, 최종 보스)
#  4페이즈 구조:  HP 100→75→50→25%
#  각 페이즈 전환마다 DEATH_NOVA (전방위 대폭발)
#  VORTEX  : 플레이어 흡입 + 주변 링
#  CHAOS_B : 초밀집 나선 탄막
#  METEOR  : 여러 각도 파도형 탄막
#  ENRAGE  : 25% 이하 – 모든 패턴 가속 + 2배 탄
# ══════════════════════════════════════════════════════════

B5_IDLE    = "B5_IDLE"
B5_VORTEX  = "B5_VORTEX"
B5_CHAOS_B = "B5_CHAOS_B"
B5_METEOR  = "B5_METEOR"
B5_NOVA    = "B5_NOVA"    # 페이즈 전환 폭발
B5_ENRAGE  = "B5_ENRAGE"


def _make_chaos_frames(size=88):
    frames=[]
    colors=[(255,60,60),(255,140,0),(200,0,255),(0,180,255)]
    for fi in range(4):
        bob=[0,-3,-5,-3][fi]
        surf=pygame.Surface((size,size),pygame.SRCALPHA)
        cx,cy=size//2,size//2+bob
        col=colors[fi]

        # 외부 회전 링
        rot=fi*25
        for i in range(8):
            a=(i/8)*math.pi*2+math.radians(rot)
            rx=cx+int(math.cos(a)*30); ry=cy+int(math.sin(a)*30)
            pygame.draw.circle(surf,col,(rx,ry),4)

        # 몸통 (팔각 별 느낌)
        pts=[]
        for i in range(8):
            a=i/8*math.pi*2; r=18 if i%2==0 else 10
            pts.append((cx+int(math.cos(a)*r),cy+int(math.sin(a)*r)))
        pygame.draw.polygon(surf,(30,10,50),pts)
        pygame.draw.polygon(surf,col,pts,2)

        # 중심 코어
        cr=[255,200,120,80][fi]
        pygame.draw.circle(surf,(cr,cr//4,cr//2),(cx,cy),10)
        pygame.draw.circle(surf,(255,255,255),(cx,cy),4)

        # 눈 (카오스 패턴)
        for ex,ey in [(cx-7,cy-5),(cx+7,cy-5)]:
            pygame.draw.circle(surf,col,(ex,ey),4)
            pygame.draw.circle(surf,(255,255,255),(ex,ey),2)

        frames.append(surf)
    return frames


class Boss5(Boss):
    NAME   = "Chaos Lord"
    MAX_HP = 1500
    RADIUS = 30
    _frames_cache = None

    def __init__(self, x, y):
        super().__init__(x, y)
        if Boss5._frames_cache is None:
            Boss5._frames_cache = _make_chaos_frames()
        self._anim          = Animation(Boss5._frames_cache, 5, loop=True)
        self._pattern       = B5_IDLE
        self._pat_timer     = random.randint(50,80)
        self._spiral_angle  = 0.0
        self._nova_done     = {1:False,2:False,3:False}   # 페이즈 전환 폭발 여부
        self._room_rect     = None
        self._alpha         = 255
        self.score          = 1000

    def _get_phase5(self):
        ratio=self.hp/self.MAX_HP
        if ratio>0.75: return 1
        if ratio>0.50: return 2
        if ratio>0.25: return 3
        return 4

    def _pick_next(self,ph):
        if ph<=2:
            return random.choice([B5_IDLE,B5_CHAOS_B,B5_VORTEX,B5_METEOR])
        if ph==3:
            return random.choice([B5_IDLE,B5_CHAOS_B,B5_VORTEX,B5_METEOR,B5_ENRAGE])
        return B5_ENRAGE

    def update(self, player, walls, room_rect=None):
        if not self.alive: return []
        if room_rect: self._room_rect=room_rect
        self._wobble+=0.06
        self._hit_timer=max(0,self._hit_timer-1)
        self._path_timer+=1
        px,py=player.x,player.y
        self.flip=(px<self.x)
        ph=self._get_phase5()
        if ph!=self.phase:
            self.phase=ph
            # 페이즈 전환 → NOVA 발동
            if not self._nova_done.get(ph,True):
                self._nova_done[ph]=True
                self._pattern=B5_NOVA
                self._pat_timer=40
        if self._path_timer>=12:
            self._path_timer=0
            self._refresh_path(px,py,walls)
        bullets=[]; self._pat_timer-=1
        enrage_mult=1.5 if ph==4 else 1.0

        # IDLE – 접근 + 부채꼴 3발
        if self._pattern==B5_IDLE:
            spd=(1.5+ph*0.4)*enrage_mult
            if math.hypot(px-self.x,py-self.y)>80:
                nx,ny=self._desired_dir(px,py)
                self._move(nx*spd,ny*spd,walls)
            self._shoot_timer-=1
            cd=max(20,50-ph*8)
            if self._shoot_timer<=0:
                self._shoot_timer=cd
                a=math.atan2(py-self.y,px-self.x)
                n=3+ph; sp=0.20
                for i in range(n):
                    bullets.append(self._bullet(a+(i-(n-1)/2)*sp,speed=5.0,damage=12,color=(200,80,255)))
            if self._pat_timer<=0:
                self._pattern=self._pick_next(ph)
                self._pat_timer=random.randint(60,90)

        # CHAOS_B – 초밀집 나선
        elif self._pattern==B5_CHAOS_B:
            cd=max(1,3-ph+1)
            if self._pat_timer%cd==0:
                self._spiral_angle+=0.18*enrage_mult
                n=2+ph
                for i in range(n):
                    a=self._spiral_angle+(2*math.pi/n)*i
                    bullets.append(self._bullet(a,speed=4.2,damage=11,color=(255,100,200)))
            if self._pat_timer<=0:
                self._pattern=self._pick_next(ph)
                self._pat_timer=random.randint(60,90)

        # VORTEX – 흡입 + 링
        elif self._pattern==B5_VORTEX:
            # 흡입 효과 (플레이어 쪽으로 자신이 아닌 탄을 안쪽으로)
            if self._pat_timer%8==0:
                # 바깥에서 안쪽으로 오는 링 (역방향 탄: 보스→플레이어 방향 반대)
                n=8+ph*2
                for i in range(n):
                    a=2*math.pi/n*i
                    # 바깥에서 안쪽으로 오도록 시작점을 바깥으로 설정
                    ox2=self.x+math.cos(a)*160; oy2=self.y+math.sin(a)*160
                    a2=math.atan2(self.y-oy2,self.x-ox2)
                    b=EnemyBullet(ox2,oy2,a2,speed=4.0,damage=10)
                    b.color=(255,120,80); bullets.append(b)
            if self._pat_timer==20:
                bullets+=self._burst(16+ph*2,speed=5.0,damage=13,color=(255,80,100))
            if self._pat_timer<=0:
                self._pattern=self._pick_next(ph)
                self._pat_timer=random.randint(60,90)

        # METEOR – 파도형 다방향 탄막
        elif self._pattern==B5_METEOR:
            waves=[(50,6,4.0,0.0),(35,6,5.0,math.pi/6),(20,8,4.5,0.0)]
            if ph>=3: waves.append((10,8,5.5,math.pi/8))
            for trigger,n,spd,off in waves:
                if self._pat_timer==trigger:
                    a=math.atan2(py-self.y,px-self.x)
                    bullets+=self._burst(n,base_angle=a,speed=spd,damage=12,offset=off)
            if self._pat_timer<=0:
                self._pattern=self._pick_next(ph)
                self._pat_timer=random.randint(60,90)

        # NOVA – 페이즈 전환 대폭발
        elif self._pattern==B5_NOVA:
            if self._pat_timer==30:
                bullets+=self._burst(24,speed=5.5,damage=15,color=(255,200,0))
                bullets+=self._burst(16,speed=3.0,damage=12,color=(255,80,80))
            if self._pat_timer<=0:
                self._pattern=self._pick_next(ph)
                self._pat_timer=random.randint(60,90)

        # ENRAGE – Phase4 전용: 모든 게 동시에
        elif self._pattern==B5_ENRAGE:
            self._spiral_angle+=0.25
            if self._pat_timer%2==0:
                a=math.atan2(py-self.y,px-self.x)
                bullets.append(self._bullet(a,speed=6.5,damage=14,color=(255,60,60)))
                bullets.append(self._bullet(self._spiral_angle,speed=4.0,damage=10,color=(200,0,255)))
                bullets.append(self._bullet(self._spiral_angle+math.pi,speed=4.0,damage=10,color=(200,0,255)))
            if self._pat_timer<=0:
                self._pattern=self._pick_next(ph)
                self._pat_timer=random.randint(40,65)

        self._anim.update()
        return bullets

    def draw(self, screen, cam_x, cam_y):
        if not self.alive: return
        sx=int(self.x)-cam_x; sy=int(self.y)-cam_y
        ph=self._get_phase5()
        # 카오스 오라 (페이즈마다 색 변화)
        aura_cols=[(200,80,255,35),(255,120,0,35),(255,0,100,45),(255,200,0,55)]
        ac=aura_cols[ph-1]
        pulse=int(abs(math.sin(self._wobble))*20)
        ao=pygame.Surface((100,100),pygame.SRCALPHA)
        pygame.draw.circle(ao,(*ac[:3],ac[3]+pulse),(50,50),42)
        screen.blit(ao,(sx-50,sy-50))
        img=self._anim.get_image().copy()
        if self._hit_timer>0 and (self._hit_timer//3)%2==0:
            fl=pygame.Surface((88,88),pygame.SRCALPHA); fl.fill((255,255,255,160)); img.blit(fl,(0,0))
        if self.flip: img=pygame.transform.flip(img,True,False)
        screen.blit(img,(sx-44,sy-44))

    def draw_boss_bar(self, screen, sw):
        bw,bh=400,20; bx=sw//2-bw//2; by=10
        p=pygame.Surface((bw+20,bh+28),pygame.SRCALPHA)
        pygame.draw.rect(p,(10,5,20,220),(0,0,bw+20,bh+28),border_radius=8)
        pygame.draw.rect(p,(200,80,255,200),(0,0,bw+20,bh+28),2,border_radius=8)
        screen.blit(p,(bx-10,by-4))
        pygame.draw.rect(screen,(30,10,50),(bx,by+8,bw,bh-4),border_radius=4)
        ratio=max(self.hp/self.MAX_HP,0)
        ph=self._get_phase5()
        bc=[(180,60,255),(255,100,0),(255,0,100),(255,200,0)][ph-1]
        if ratio>0: pygame.draw.rect(screen,bc,(bx,by+8,int(bw*ratio),bh-4),border_radius=4)
        pygame.draw.rect(screen,(255,180,255),(bx,by+8,bw,bh-4),2,border_radius=4)
        # 4페이즈 경계선
        for frac in [0.75,0.50,0.25]:
            lx=bx+int(bw*frac)
            pygame.draw.line(screen,(255,255,100),(lx,by+6),(lx,by+bh+4),1)
        font=pygame.font.SysFont(None,22)
        nc=[(220,120,255),(255,160,60),(255,80,140),(255,220,60)][ph-1]
        screen.blit(font.render(f"{self.NAME}  ─  Phase {ph}/4",True,nc),(bx,by-1))
        pat={B5_IDLE:"...",B5_CHAOS_B:"↻ CHAOS",B5_VORTEX:"◎ VORTEX",B5_METEOR:"↓ METEOR",B5_NOVA:"★ NOVA ★",B5_ENRAGE:"!!! ENRAGE !!!"}
        pt=font.render(pat.get(self._pattern,""),True,nc)
        screen.blit(pt,(bx+bw-pt.get_width(),by-1))