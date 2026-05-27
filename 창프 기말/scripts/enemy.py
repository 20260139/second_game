# scripts/enemy.py

import pygame, math, random, base64, heapq
from io import BytesIO
from scripts.bullet import EnemyBullet
from scripts import enemy_sprites
from scripts.animation import Animation

CELL_E    = 32   # 적 스프라이트 셀 크기
DRAW_SIZE = 36   # 렌더 크기
TILE      = 32   # 탐색 그리드 단위

def _load_enemy_frames(b64_data, n_frames):
    raw   = base64.b64decode(b64_data)
    sheet = pygame.image.load(BytesIO(raw)).convert_alpha()
    frames = []
    for i in range(n_frames):
        rect  = pygame.Rect(i * CELL_E, 0, CELL_E, CELL_E)
        frame = pygame.transform.scale(
            sheet.subsurface(rect).copy(), (DRAW_SIZE, DRAW_SIZE)
        )
        frames.append(frame)
    return frames


# ── A* 경로 탐색 ─────────────────────────────────────────────

def _build_wall_set(walls):
    """pygame.Rect 목록 → 타일 좌표 set (빠른 충돌 확인용)"""
    blocked = set()
    for w in walls:
        # 벽 rect 가 걸치는 모든 타일을 막힌 셀로 등록
        tx0 = w.left  // TILE
        ty0 = w.top   // TILE
        tx1 = (w.right  - 1) // TILE
        ty1 = (w.bottom - 1) // TILE
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                blocked.add((tx, ty))
    return blocked


def _astar(start_px, start_py, goal_px, goal_py, wall_set, radius):
    """
    픽셀 좌표 → 픽셀 waypoint 리스트 반환 (A*).
    반환값: [(wx, wy), ...] 목표 방향의 다음 웨이포인트들.
           경로 없으면 [] 반환.
    """
    # 타일 좌표로 변환
    sx, sy = start_px // TILE, start_py // TILE
    gx, gy = goal_px  // TILE, goal_py  // TILE

    if (sx, sy) == (gx, gy):
        return []

    # 에이전트 반경을 타일 단위로 올림 → 통로 여유 확보
    r_tiles = max(1, math.ceil(radius / TILE))

    def passable(tx, ty):
        # 에이전트 크기를 고려해 주변 셀도 체크
        # r_tiles=1일 때 자기 셀 + 인접 셀 체크 (1타일 통로도 통과 가능하도록 범위 최소화)
        for dy in range(-(r_tiles - 1), r_tiles):
            for dx in range(-(r_tiles - 1), r_tiles):
                if (tx + dx, ty + dy) in wall_set:
                    return False
        return True

    def heuristic(tx, ty):
        return abs(tx - gx) + abs(ty - gy)

    # 8방향 이동 (대각선 포함)
    NEIGHBORS = [
        (1,0,1.0),(-1,0,1.0),(0,1,1.0),(0,-1,1.0),
        (1,1,1.414),(-1,1,1.414),(1,-1,1.414),(-1,-1,1.414),
    ]

    open_heap = []   # (f, g, tx, ty)
    heapq.heappush(open_heap, (heuristic(sx, sy), 0.0, sx, sy))
    came_from = {}
    g_score   = {(sx, sy): 0.0}

    # 탐색 범위 제한 (방 크기 기준, 최대 400셀)
    MAX_ITER = 400

    for _ in range(MAX_ITER):
        if not open_heap:
            break
        f, g, cx, cy = heapq.heappop(open_heap)

        if (cx, cy) == (gx, gy):
            # 경로 역추적
            path = []
            node = (cx, cy)
            while node in came_from:
                path.append(node)
                node = came_from[node]
            path.reverse()
            # 타일 중심 픽셀로 변환
            return [(tx * TILE + TILE // 2, ty * TILE + TILE // 2)
                    for tx, ty in path]

        for ddx, ddy, cost in NEIGHBORS:
            nx, ny = cx + ddx, cy + ddy
            if not passable(nx, ny):
                continue
            ng = g + cost
            if ng < g_score.get((nx, ny), float('inf')):
                g_score[(nx, ny)] = ng
                came_from[(nx, ny)] = (cx, cy)
                heapq.heappush(open_heap,
                               (ng + heuristic(nx, ny), ng, nx, ny))

    return []   # 경로 없음


class Enemy:

    TYPES = {
        "slime": {
            "color"    : (80, 200, 80),
            "outline"  : (40, 120, 40),
            "radius"   : 14,
            "hp"       : 60,
            "speed"    : 1.2,
            "damage"   : 10,
            "atk_range": 20,
            "atk_cd"   : 60,
            "shoot"    : False,
            "score"    : 10,
            "b64"      : "SLIME_WALK",
            "n_frames" : 4,
            "anim_spd" : 8,
        },
        "bat": {
            "color"    : (160, 80, 200),
            "outline"  : (90, 40, 130),
            "radius"   : 11,
            "hp"       : 40,
            "speed"    : 2.0,
            "damage"   : 7,
            "atk_range": 18,
            "atk_cd"   : 45,
            "shoot"    : False,
            "score"    : 15,
            "b64"      : "BAT_WALK",
            "n_frames" : 4,
            "anim_spd" : 5,
        },
        "archer": {
            "color"    : (200, 120, 60),
            "outline"  : (140, 70, 30),
            "radius"   : 13,
            "hp"       : 80,
            "speed"    : 0.9,
            "damage"   : 15,
            "atk_range": 300,
            "atk_cd"   : 90,
            "shoot"    : True,
            "score"    : 25,
            "b64"      : "ARCHER_WALK",
            "n_frames" : 4,
            "anim_spd" : 10,
        },
    }

    _frame_cache = {}

    def __init__(self, x, y, kind="slime"):
        cfg = self.TYPES[kind]
        self.x       = float(x)
        self.y       = float(y)
        self.kind    = kind
        self.radius  = cfg["radius"]
        self.max_hp  = cfg["hp"]
        self.hp      = cfg["hp"]
        self.speed   = cfg["speed"]
        self.damage  = cfg["damage"]
        self.atk_range = cfg["atk_range"]
        self.atk_cd  = cfg["atk_cd"]
        self.shoot   = cfg["shoot"]
        self.score   = cfg["score"]
        self.color   = cfg["color"]
        self.outline = cfg["outline"]
        self.alive   = True

        self._atk_timer = random.randint(0, cfg["atk_cd"])
        self._hit_timer = 0
        self._wobble    = random.uniform(0, math.pi * 2)
        self.flip       = False

        # 애니메이션
        self._anim        = None
        self._anim_loaded = False
        self._cfg         = cfg

        # ── 경로 탐색 ──────────────────────────────────────
        self._path        = []          # 웨이포인트 리스트 [(px,py), ...]
        self._path_timer  = 20          # 첫 갱신을 빠르게 (10프레임 후)
        self._wall_set    = None        # 캐시된 wall_set
        self._wall_set_id = None        # walls 리스트 id (변경 감지용)
        # 직선 시야 확인용: True이면 A* 없이 직선 이동
        self._has_los     = False
        # 방 활성화 여부: True 이후부터 추적 시작
        self._activated   = False

    # ── 애니메이션 ────────────────────────────────────────

    def _ensure_anim(self):
        if self._anim_loaded:
            return
        key = self.kind
        if key not in Enemy._frame_cache:
            b64_data = getattr(enemy_sprites, self._cfg["b64"])
            Enemy._frame_cache[key] = _load_enemy_frames(
                b64_data, self._cfg["n_frames"]
            )
        self._anim = Animation(
            Enemy._frame_cache[key],
            self._cfg["anim_spd"],
            loop=True
        )
        self._anim_loaded = True

    def get_rect(self):
        r = self.radius
        return pygame.Rect(int(self.x)-r, int(self.y)-r, r*2, r*2)

    # ── 시야선(LOS) 확인 ─────────────────────────────────

    def _check_los(self, px, py, wall_set):
        """
        적 → 플레이어 직선 경로에 벽이 없으면 True.
        타일 단위로 브레젠험 라인 검사.
        """
        sx, sy = int(self.x) // TILE, int(self.y) // TILE
        gx, gy = int(px)     // TILE, int(py)     // TILE

        dx, dy = abs(gx - sx), abs(gy - sy)
        xstep  = 1 if gx > sx else -1
        ystep  = 1 if gy > sy else -1
        cx, cy = sx, sy
        err    = dx - dy

        for _ in range(dx + dy + 2):
            if (cx, cy) in wall_set:
                return False
            if (cx, cy) == (gx, gy):
                return True
            e2 = err * 2
            if e2 > -dy:
                err -= dy
                cx  += xstep
            if e2 < dx:
                err += dx
                cy  += ystep
        return True

    # ── 경로 탐색 갱신 ───────────────────────────────────

    def _get_wall_set(self, walls):
        """walls 리스트가 바뀌었을 때만 wall_set 재빌드."""
        wid = id(walls)
        if wid != self._wall_set_id:
            self._wall_set    = _build_wall_set(walls)
            self._wall_set_id = wid
        return self._wall_set

    def activate(self, px, py, walls):
        """방 활성화 시 즉시 경로 계산 (첫 프레임 멈춤 방지)."""
        self._activated  = True
        self._path_timer = 20          # 즉시 갱신 트리거
        self._refresh_path(px, py, walls)

    def _refresh_path(self, px, py, walls):
        """A* 경로 재계산. 직선 시야면 경로 비움."""
        wall_set = self._get_wall_set(walls)
        self._has_los = self._check_los(px, py, wall_set)
        if self._has_los:
            self._path = []
        else:
            self._path = _astar(
                int(self.x), int(self.y),
                int(px),     int(py),
                wall_set, self.radius
            )

    # ── 이동 방향 결정 ───────────────────────────────────

    def _desired_direction(self, px, py):
        """
        현재 경로/시야에 따라 이동할 방향 벡터 (nx, ny) 반환.
        이동 불필요하면 (0, 0).
        """
        if self._has_los:
            # 직선 시야: 플레이어 방향으로 직진
            dx = px - self.x
            dy = py - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                return dx / dist, dy / dist
            return 0.0, 0.0

        # 경로 추종
        if not self._path:
            # ── fallback: 경로 없어도 플레이어 방향으로 직접 이동 ──
            # (A* 계산 전 첫 프레임, 또는 경로 탐색 실패 시)
            dx = px - self.x
            dy = py - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                return dx / dist, dy / dist
            return 0.0, 0.0

        # 현재 웨이포인트에 충분히 가까우면 다음 웨이포인트로
        wx, wy = self._path[0]
        d = math.hypot(wx - self.x, wy - self.y)
        if d < TILE * 0.6:
            self._path.pop(0)
            if not self._path:
                return 0.0, 0.0
            wx, wy = self._path[0]
            d = math.hypot(wx - self.x, wy - self.y)

        if d > 0:
            return (wx - self.x) / d, (wy - self.y) / d
        return 0.0, 0.0

    # ── 메인 업데이트 ─────────────────────────────────────

    def update(self, player, walls):
        if not self.alive:
            return None

        self._hit_timer  = max(0, self._hit_timer - 1)
        self._atk_timer  = max(0, self._atk_timer - 1)
        self._wobble    += 0.05

        px, py = player.x, player.y
        dx_p   = px - self.x
        dy_p   = py - self.y
        dist   = math.hypot(dx_p, dy_p)

        # flip 방향
        self.flip = dx_p < 0

        bullet_out = None

        if dist < 600:   # 어그로 범위
            # ── 경로 갱신 (15프레임마다, 분산 처리) ──────
            self._path_timer += 1
            if self._path_timer >= 15:
                self._path_timer = 0
                self._refresh_path(px, py, walls)

            # ── 이동 ──────────────────────────────────────
            if dist > self.atk_range * 0.8:
                nx, ny = self._desired_direction(px, py)
                if nx != 0 or ny != 0:
                    self._move(nx * self.speed, ny * self.speed, walls)

            # ── 공격 ──────────────────────────────────────
            if dist <= self.atk_range and self._atk_timer <= 0:
                self._atk_timer = self.atk_cd
                if self.shoot:
                    angle = math.atan2(dy_p, dx_p)
                    bullet_out = EnemyBullet(self.x, self.y, angle,
                                            damage=self.damage)

        # 애니메이션
        if self._anim_loaded and self._anim:
            self._anim.update()

        return bullet_out

    def update_idle(self, walls):
        """어그로 없는 상태: 타이머만 갱신."""
        if not self.alive:
            return None
        self._hit_timer = max(0, self._hit_timer - 1)
        self._atk_timer = max(0, self._atk_timer - 1)
        self._wobble   += 0.05
        if self._anim_loaded and self._anim:
            self._anim.update()
        return None

    # ── 충돌 이동 ─────────────────────────────────────────

    def _move(self, dx, dy, walls):
        """축 분리 이동 + 슬라이딩 충돌 해소."""
        r = self.radius

        # X축 이동
        if dx != 0:
            self.x += dx
            rect = pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)
            for wall in walls:
                if rect.colliderect(wall):
                    if dx > 0:
                        self.x = wall.left - r
                    else:
                        self.x = wall.right + r
                    rect.x = int(self.x) - r

        # Y축 이동
        if dy != 0:
            self.y += dy
            rect = pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)
            for wall in walls:
                if rect.colliderect(wall):
                    if dy > 0:
                        self.y = wall.top - r
                    else:
                        self.y = wall.bottom + r
                    rect.y = int(self.y) - r

    def take_damage(self, amount):
        self.hp -= amount
        self._hit_timer = 12
        # 피격 시 즉시 경로 갱신 트리거 (다음 update에서 바로 재계산)
        self._path_timer = 20
        if self.hp <= 0:
            self.alive = False

    def draw(self, screen, cam_x, cam_y):
        if not self.alive:
            return

        self._ensure_anim()

        sx = int(self.x) - cam_x
        sy = int(self.y) - cam_y

        if self._anim:
            img = self._anim.get_image()

            if self._hit_timer > 0 and (self._hit_timer // 3) % 2 == 0:
                img2 = self._anim.get_image().copy()
                img2.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_ADD)
                img = img2

            if self.flip:
                img = pygame.transform.flip(img, True, False)

            draw_x = sx - DRAW_SIZE // 2
            draw_y = sy - DRAW_SIZE // 2
            screen.blit(img, (draw_x, draw_y))

            if self._hit_timer > 0 and (self._hit_timer // 3) % 2 == 0:
                flash = pygame.Surface((DRAW_SIZE, DRAW_SIZE), pygame.SRCALPHA)
                flash.fill((255, 255, 255, 120))
                screen.blit(flash, (draw_x, draw_y))
        else:
            if self._hit_timer > 0 and (self._hit_timer // 3) % 2 == 0:
                draw_color = (255, 255, 255)
            else:
                draw_color = self.color
            pygame.draw.circle(screen, self.outline, (sx, sy), self.radius + 2)
            pygame.draw.circle(screen, draw_color,   (sx, sy), self.radius)

        # HP 바
        bar_w = self.radius * 2
        bx = sx - self.radius
        by = sy - self.radius - 8
        pygame.draw.rect(screen, (60, 20, 20), (bx, by, bar_w, 4))
        ratio = max(self.hp / self.max_hp, 0)
        pygame.draw.rect(screen, (80, 220, 80), (bx, by, int(bar_w * ratio), 4))
