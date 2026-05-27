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

    def update(self, player, walls):
        """반환값: 발사된 EnemyBullet 리스트"""
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
