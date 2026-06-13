# scripts/stage1.py

import pygame, math, random
from scripts.enemy    import Enemy
from scripts.merchant import Merchant
from scripts.boss  import Boss, Boss2, Boss3, Boss4, Boss5
from scripts.bullet import Bullet

TILE           = 32
MAX_ROOMS      = 7
ROOM_W         = 15
ROOM_H         = 11
CORRIDOR_LEN   = 5
CORRIDOR_THICK = 3

C_FLOOR       = (45,  38,  60)
C_FLOOR2      = (38,  32,  52)
C_WALL        = (28,  22,  45)
C_WALL_TOP    = (55,  45,  80)
C_DOOR_OPEN   = (60, 160,  80)
C_DOOR_CLOSE  = (160, 60,  60)
C_COIN        = (255, 210,  40)
C_EXIT        = (100, 240, 160)
C_BOSS_FLOOR  = (60,  30,  30)
C_BOSS_FLOOR2 = (50,  22,  22)

DIRS     = {'right':(1,0),'left':(-1,0),'down':(0,1),'up':(0,-1)}
OPPOSITE = {'right':'left','left':'right','up':'down','down':'up'}

# 방 입장 감지 여백: 벽 1타일 안쪽에 발을 딛는 순간 즉시 문이 닫힘
# TILE+2 로 설정 → 복도를 막 벗어나 방 경계를 넘자마자 잠금
ROOM_INNER_MARGIN = TILE + 10


# ── 헬퍼 ──────────────────────────────────────────────────

def _room_pixel(grid_x, grid_y):
    step_x = (ROOM_W + CORRIDOR_LEN) * TILE
    step_y = (ROOM_H + CORRIDOR_LEN) * TILE
    return (300 + grid_x * step_x, 300 + grid_y * step_y)


def _room_walls(rx, ry, rw, rh, open_dirs):
    """외곽 벽. open_dirs 방향에 통로 구멍을 냄."""
    walls = []
    T  = TILE
    ht = CORRIDOR_THICK // 2   # 통로 중심 오프셋

    for c in range(rw):
        x = rx + c * T
        gap_up   = 'up'   in open_dirs and (rw//2 - ht) <= c < (rw//2 - ht + CORRIDOR_THICK)
        gap_down = 'down' in open_dirs and (rw//2 - ht) <= c < (rw//2 - ht + CORRIDOR_THICK)
        if not gap_up:
            walls.append(pygame.Rect(x, ry, T, T))
        if not gap_down:
            walls.append(pygame.Rect(x, ry + (rh-1)*T, T, T))

    for r in range(1, rh-1):
        y = ry + r * T
        gap_left  = 'left'  in open_dirs and (rh//2 - ht) <= r < (rh//2 - ht + CORRIDOR_THICK)
        gap_right = 'right' in open_dirs and (rh//2 - ht) <= r < (rh//2 - ht + CORRIDOR_THICK)
        if not gap_left:
            walls.append(pygame.Rect(rx, y, T, T))
        if not gap_right:
            walls.append(pygame.Rect(rx + (rw-1)*T, y, T, T))

    return walls


def _room_floor(rx, ry, rw, rh, is_boss=False):
    return [(rx+c*TILE, ry+r*TILE, is_boss) for r in range(rh) for c in range(rw)]


def _corridor_walls_and_floor(room_px, room_py, direction):
    T  = TILE
    RW = ROOM_W  * T
    RH = ROOM_H  * T
    CL = CORRIDOR_LEN   * T
    CT = CORRIDOR_THICK * T
    walls, floors = [], []

    if direction == 'right':
        ox, oy = room_px + RW, room_py + RH//2 - CT//2
        floors += [(ox+c*T, oy+r*T, False) for r in range(CORRIDOR_THICK) for c in range(CORRIDOR_LEN)]
        walls  += [pygame.Rect(ox, oy-T, CL, T), pygame.Rect(ox, oy+CT, CL, T)]
    elif direction == 'left':
        ox, oy = room_px - CL, room_py + RH//2 - CT//2
        floors += [(ox+c*T, oy+r*T, False) for r in range(CORRIDOR_THICK) for c in range(CORRIDOR_LEN)]
        walls  += [pygame.Rect(ox, oy-T, CL, T), pygame.Rect(ox, oy+CT, CL, T)]
    elif direction == 'down':
        ox, oy = room_px + RW//2 - CT//2, room_py + RH
        floors += [(ox+c*T, oy+r*T, False) for r in range(CORRIDOR_LEN) for c in range(CORRIDOR_THICK)]
        walls  += [pygame.Rect(ox-T, oy, T, CL), pygame.Rect(ox+CT, oy, T, CL)]
    elif direction == 'up':
        ox, oy = room_px + RW//2 - CT//2, room_py - CL
        floors += [(ox+c*T, oy+r*T, False) for r in range(CORRIDOR_LEN) for c in range(CORRIDOR_THICK)]
        walls  += [pygame.Rect(ox-T, oy, T, CL), pygame.Rect(ox+CT, oy, T, CL)]

    return walls, floors


# ── Coin ──────────────────────────────────────────────────

class Coin:
    def __init__(self, x, y, value=5):
        self.x = x; self.y = y; self.value = value
        self.alive = True; self._t = 0

    def update(self): self._t += 1

    def draw(self, screen, cam_x, cam_y):
        if not self.alive: return
        sx, sy = int(self.x)-cam_x, int(self.y)-cam_y
        bob = int(math.sin(self._t*0.1)*3)
        pygame.draw.circle(screen, (200,160,20), (sx, sy+bob), 7)
        pygame.draw.circle(screen, C_COIN,       (sx, sy+bob), 5)


# ── Room ──────────────────────────────────────────────────

class Room:
    def __init__(self, grid_x, grid_y, open_dirs, room_idx,
                 is_start=False, is_boss=False):
        self.grid_x    = grid_x
        self.grid_y    = grid_y
        self.open_dirs = open_dirs
        self.room_idx  = room_idx
        self.is_start  = is_start
        self.is_boss   = is_boss

        # cleared: 적 전멸 여부  /  locked: 현재 문이 닫혀 있는 상태
        self.cleared      = is_start
        self.locked       = False
        self.activated    = is_start
        self.reward_given = is_start   # 시작방은 보상 없음

        px, py = _room_pixel(grid_x, grid_y)
        self.px = px
        self.py = py
        self.rw = ROOM_W * TILE
        self.rh = ROOM_H * TILE

    def center(self):
        return (self.px + self.rw//2, self.py + self.rh//2)

    def inner_rect(self):
        """벽 안쪽 영역 (플레이어가 '방 안'으로 판정되는 영역)"""
        m = ROOM_INNER_MARGIN
        return pygame.Rect(self.px + m, self.py + m,
                           self.rw - m*2, self.rh - m*2)

    def contains(self, x, y):
        return (self.px <= x <= self.px + self.rw and
                self.py <= y <= self.py + self.rh)


# ── Stage1 ────────────────────────────────────────────────

class Stage1:

    def __init__(self, player, stage_num=1, sm=None):
        self.player    = player
        self.stage_num = stage_num
        self._sm = sm           # SoundManager (BGM 전환용)
        self._boss_bgm_playing = False
        self.merchant = Merchant()
        self._dice_roll   = {}      # 현재 팝업 주사위 결과
        self._dice_rolling= {}      # 굴림 애니 잔여 틱
        self._dice_show   = {}      # 굴림 중 임시 값
        self._dice_rects  = {}      # 주사위 클릭 영역
        self.bullets       = []
        self.e_bullets     = []
        self.slash_effects = []   # 참격 SlashWave 투사체
        self.enemies   = []
        self.coins     = []
        self.boss      = None   # 보스 인스턴스 (보스방 입장 시 활성화)
        self._tick     = 0
        self.current_room_idx = 0
        self._visited_rooms   = set()   # 방문한 room_idx 집합

        self._generate_map()
        self._build_geometry()
        self._spawn_all_enemies()

        cx, cy = self.rooms[0].center()
        player.x = float(cx)
        player.y = float(cy)

        # 시작방은 처음부터 방문 처리
        start_room = next((r for r in self.rooms if r.is_start), None)
        if start_room:
            self._visited_rooms.add(start_room.room_idx)

        # 스테이지 난이도 스케일링 (스탯 배율)
        # 층마다 HP +50%, 속도 +15%, 데미지 +20% 복리 증가
        n = self.stage_num - 1
        hp_mult  = 1.0 + n * 0.50
        spd_mult = 1.0 + n * 0.15
        dmg_mult = 1.0 + n * 0.20
        for e in self.enemies:
            e.max_hp = int(e.max_hp * hp_mult)
            e.hp     = e.max_hp
            e.speed  = round(e.speed * spd_mult, 2)
            e.damage = int(e.damage * dmg_mult)
        if self.boss:
            self.boss.hp = self.boss.MAX_HP

    # ── 맵 생성 ──────────────────────────────────────────

    def _generate_map(self):
        grid, rooms = {}, []
        start = Room(0, 0, set(), 0, is_start=True)
        grid[(0,0)] = start
        rooms.append(start)
        frontier, room_count = [start], 1

        while frontier and room_count < MAX_ROOMS:
            random.shuffle(frontier)
            current = frontier.pop(0)
            dir_list = list(DIRS.keys())
            random.shuffle(dir_list)
            for d in dir_list:
                if room_count >= MAX_ROOMS:
                    break
                dx, dy = DIRS[d]
                nx, ny = current.grid_x+dx, current.grid_y+dy
                if (nx,ny) in grid:
                    continue
                is_boss = (room_count == MAX_ROOMS-1)
                nr = Room(nx, ny, set(), room_count, is_boss=is_boss)
                grid[(nx,ny)] = nr
                rooms.append(nr)
                room_count += 1
                current.open_dirs.add(d)
                nr.open_dirs.add(OPPOSITE[d])
                frontier.append(nr)

        self.rooms = rooms
        self.grid  = grid

    def _build_geometry(self):
        self.walls  = []
        self.floors = []
        # door_rects[room_idx][dir] = Rect  (문 위치, 닫힐 때 벽으로 사용)
        self.door_rects = {}
        visited = set()

        for room in self.rooms:
            px, py = room.px, room.py
            self.walls  += _room_walls(px, py, ROOM_W, ROOM_H, room.open_dirs)
            self.floors += _room_floor(px, py, ROOM_W, ROOM_H, room.is_boss)
            if not room.is_start:
                self._add_obstacles(px, py, room.room_idx)

            # 문 Rect 계산
            T  = TILE
            CT = CORRIDOR_THICK * T
            RW = ROOM_W * T
            RH = ROOM_H * T
            ht = CORRIDOR_THICK // 2
            door_d = {}
            for d in room.open_dirs:
                if d == 'right':
                    dr = pygame.Rect(px+RW-T,        py+RH//2-CT//2, T,  CT)
                elif d == 'left':
                    dr = pygame.Rect(px,             py+RH//2-CT//2, T,  CT)
                elif d == 'down':
                    dr = pygame.Rect(px+RW//2-CT//2, py+RH-T,        CT, T)
                elif d == 'up':
                    dr = pygame.Rect(px+RW//2-CT//2, py,             CT, T)
                door_d[d] = dr
            self.door_rects[room.room_idx] = door_d

            # 통로
            for d in room.open_dirs:
                key = tuple(sorted([(room.grid_x,room.grid_y),
                                    (room.grid_x+DIRS[d][0], room.grid_y+DIRS[d][1])]))
                if key in visited:
                    continue
                visited.add(key)
                cw, cf = _corridor_walls_and_floor(px, py, d)
                self.walls  += cw
                self.floors += cf

        # 보스방 출구
        boss = next(r for r in self.rooms if r.is_boss)
        T=TILE; CT=CORRIDOR_THICK*T; RW=ROOM_W*T; RH=ROOM_H*T
        ed = list(boss.open_dirs)[0]
        bpx, bpy = boss.px, boss.py
        if   ed=='right': self.exit_rect = pygame.Rect(bpx+RW-T, bpy+RH//2-CT//2, T, CT)
        elif ed=='left' : self.exit_rect = pygame.Rect(bpx,      bpy+RH//2-CT//2, T, CT)
        elif ed=='down' : self.exit_rect = pygame.Rect(bpx+RW//2-CT//2, bpy+RH-T, CT, T)
        else            : self.exit_rect = pygame.Rect(bpx+RW//2-CT//2, bpy,      CT, T)

    def _add_obstacles(self, ox, oy, room_idx):
        T = TILE
        patterns = [
            [(2,2),(2,3),(ROOM_W-3,2),(ROOM_W-3,3),
             (2,ROOM_H-4),(2,ROOM_H-5),(ROOM_W-3,ROOM_H-4),(ROOM_W-3,ROOM_H-5)],
            [(ROOM_W//2-1,3),(ROOM_W//2,3),(ROOM_W//2+1,3),
             (ROOM_W//2-1,ROOM_H-4),(ROOM_W//2,ROOM_H-4),(ROOM_W//2+1,ROOM_H-4),
             (2,ROOM_H//2),(3,ROOM_H//2),(ROOM_W-4,ROOM_H//2),(ROOM_W-3,ROOM_H//2)],
            [(3,3),(4,3),(5,3),(3,4),(3,5),
             (ROOM_W-5,ROOM_H-4),(ROOM_W-4,ROOM_H-4),(ROOM_W-5,ROOM_H-5)],
            [(ROOM_W//2-2,ROOM_H//2-2),(ROOM_W//2-1,ROOM_H//2-2),(ROOM_W//2,ROOM_H//2-2),
             (ROOM_W//2-2,ROOM_H//2-1),(ROOM_W//2-2,ROOM_H//2),
             (ROOM_W//2,ROOM_H//2-1),(ROOM_W//2,ROOM_H//2)],
        ]
        for c, r in patterns[room_idx % len(patterns)]:
            self.walls.append(pygame.Rect(ox+c*T, oy+r*T, T, T))

    def _spawn_all_enemies(self):
        T=TILE; RW=ROOM_W*T; RH=ROOM_H*T
        s = self.stage_num   # 1~5

        # 층별 종류 풀 및 기본 마릿수
        # stage 1: 슬라임/박쥐  stage 3+: 궁수 추가  stage 4+: 중후반 비중 조정
        if s <= 1:
            pool_early = ["slime","slime","bat"]
            pool_mid   = ["slime","bat","bat"]
            pool_late  = ["slime","bat","bat"]
        elif s == 2:
            pool_early = ["slime","slime","bat"]
            pool_mid   = ["slime","bat","archer"]
            pool_late  = ["bat","bat","archer"]
        elif s == 3:
            pool_early = ["slime","bat","archer"]
            pool_mid   = ["bat","archer","archer"]
            pool_late  = ["bat","archer","archer"]
        elif s == 4:
            pool_early = ["bat","archer","archer"]
            pool_mid   = ["bat","archer","archer"]
            pool_late  = ["archer","archer","archer"]
        else:  # s == 5
            pool_early = ["bat","archer","archer"]
            pool_mid   = ["archer","archer","archer"]
            pool_late  = ["archer","archer","archer"]

        # 기본 마릿수: 층마다 +1 (최대 8마리)
        base_early = min(3 + (s - 1),     8)
        base_mid   = min(4 + (s - 1),     8)
        base_late  = min(4 + (s - 1),     8)

        # 보스방 잡몹도 층마다 +1
        boss_minion_count = min(2 + (s - 1), 6)

        for room in self.rooms:
            if room.is_start:
                continue
            ox, oy = room.px, room.py
            if room.is_boss:
                cx = ox + RW//2
                cy = oy + RH//2
                BOSS_MAP = {1: Boss, 2: Boss2, 3: Boss3, 4: Boss4, 5: Boss5}
                BossClass = BOSS_MAP.get(self.stage_num, Boss)
                self.boss = BossClass(float(cx), float(cy))
                self.boss._room_idx = room.room_idx
                # 보스방 잡몹 (층마다 증가)
                minion_pool = pool_late
                kinds = random.choices(minion_pool, k=boss_minion_count)
                for kind in kinds:
                    ex = ox + T*2 + random.randint(0, RW-T*4)
                    ey = oy + T*2 + random.randint(0, RH-T*4)
                    e  = Enemy(ex, ey, kind)
                    e._room_idx = room.room_idx
                    self.enemies.append(e)
            elif room.room_idx <= 2:
                kinds = random.choices(pool_early, k=base_early)
                for kind in kinds:
                    ex = ox + T*2 + random.randint(0, RW-T*4)
                    ey = oy + T*2 + random.randint(0, RH-T*4)
                    e  = Enemy(ex, ey, kind)
                    e._room_idx = room.room_idx
                    self.enemies.append(e)
            elif room.room_idx <= 4:
                kinds = random.choices(pool_mid, k=base_mid)
                for kind in kinds:
                    ex = ox + T*2 + random.randint(0, RW-T*4)
                    ey = oy + T*2 + random.randint(0, RH-T*4)
                    e  = Enemy(ex, ey, kind)
                    e._room_idx = room.room_idx
                    self.enemies.append(e)
            else:
                kinds = random.choices(pool_late, k=base_late)
                for kind in kinds:
                    ex = ox + T*2 + random.randint(0, RW-T*4)
                    ey = oy + T*2 + random.randint(0, RH-T*4)
                    e  = Enemy(ex, ey, kind)
                    e._room_idx = room.room_idx
                    self.enemies.append(e)

    # ── 유틸 ─────────────────────────────────────────────

    def _current_room(self):
        p = self.player
        for room in self.rooms:
            if room.contains(p.x, p.y):
                return room
        return self.rooms[0]

    def _enemies_in_room(self, room_idx):
        return [e for e in self.enemies
                if e.alive and getattr(e,'_room_idx',None)==room_idx]

    def _current_walls(self):
        """정적 벽 + 현재 locked된 방의 문 벽"""
        walls = list(self.walls)
        for room in self.rooms:
            if room.locked:          # locked 상태일 때만 문이 벽으로 작동
                for dr in self.door_rects[room.room_idx].values():
                    walls.append(dr)
        return walls

    # 월드를 그릴 뷰포트 크기 (800x600보다 작을수록 줌인)
    ZOOM_W = 620
    ZOOM_H = 465
    # 가상 캔버스 기준 크기 (main.py BASE_W, BASE_H 와 동일)
    CANVAS_W = 800
    CANVAS_H = 600

    def _get_cam(self, screen=None):
        """항상 ZOOM 뷰포트 기준으로 카메라 계산"""
        p = self.player
        cam_x = int(p.x) - self.ZOOM_W // 2
        cam_y = int(p.y) - self.ZOOM_H // 2
        return cam_x, cam_y

    def _canvas_to_vp(self, pos):
        """
        캔버스 좌표(0~CANVAS_W, 0~CANVAS_H) →
        뷰포트 좌표(0~ZOOM_W, 0~ZOOM_H) 변환.
        줌인 후 마우스 위치·조준 각도 계산에 사용.
        """
        cx, cy = pos
        vx = cx * self.ZOOM_W / self.CANVAS_W
        vy = cy * self.ZOOM_H / self.CANVAS_H
        return (int(vx), int(vy))

    # ── 이벤트 ───────────────────────────────────────────

    # ── 업데이트 ─────────────────────────────────────────

    def update(self, keys, mouse_pos, gm):
        # 방 클리어 보상 팝업 트리거
        if getattr(gm, 'pending_room_clear', False):
            gm.pending_room_clear = False
            self._start_dice()
            gm.state = "ROOM_CLEAR"
            return

        self._tick += 1
        p     = self.player
        walls = self._current_walls()
        cam_x, cam_y = self._get_cam()

        # 캔버스 좌표 -> 뷰포트 좌표로 변환 (flip 방향·조준 판정에 사용)
        vp_mouse = self._canvas_to_vp(mouse_pos)
        p.handle_input(keys, vp_mouse, walls, cam_x, cam_y)

        # ── 근접 공격 판정 — p.update() 전에 플래그 소비 ──
        melee_ok, _ = p.consume_melee()

        p.update()

        if melee_ok:
            for e in self.enemies:
                if not e.alive:
                    continue
                room_of_e = next((r for r in self.rooms
                                  if r.room_idx == getattr(e, '_room_idx', None)), None)
                if not (room_of_e and room_of_e.activated and not room_of_e.cleared):
                    continue
                if p.melee_hits(e.x, e.y):
                    e.take_damage(p.damage)
                    if not e.alive:
                        gm.score += e.score
                        for _ in range(random.randint(1, 3)):
                            self.coins.append(Coin(
                                e.x + random.randint(-20, 20),
                                e.y + random.randint(-20, 20), 5))
            if self.boss and not self.boss.is_dead():
                boss_room = next((r for r in self.rooms if r.is_boss), None)
                if boss_room and boss_room.activated and not boss_room.cleared:
                    if p.melee_hits(self.boss.x, self.boss.y):
                        self.boss.take_damage(p.damage)
                        if self.boss.is_dead():
                            gm.score += self.boss.score
                            gm.reroll_tickets += 1   # 보스 처치 → 리롤권 1개 드롭
                            for _ in range(random.randint(5, 8)):
                                self.coins.append(Coin(
                                    self.boss.x + random.randint(-30, 30),
                                    self.boss.y + random.randint(-30, 30), 10))

        cur_room = self._current_room()
        self.current_room_idx = cur_room.room_idx

        # ── 방 입장 감지 → 방문 기록 + 문 잠금 + 어그로 ──
        for room in self.rooms:
            # 방문 기록 (클리어 여부와 무관)
            if room.inner_rect().collidepoint(p.x, p.y):
                self._visited_rooms.add(room.room_idx)

            if room.is_start or room.cleared or room.activated:
                continue
            # 플레이어가 방 내부(벽 안쪽)에 완전히 들어왔을 때
            if room.inner_rect().collidepoint(p.x, p.y):
                room.activated = True
                room.locked    = True   # 문 닫힘
                # ── 해당 방 적들에게 즉시 경로 계산 트리거 ──
                room_enemies = self._enemies_in_room(room.room_idx)
                for e in room_enemies:
                    e.activate(p.x, p.y, walls)
                # ── 보스방 입장 시 보스 활성화 ──────────────
                if room.is_boss and self.boss and not self.boss.is_dead():
                    self.boss.activate(p.x, p.y, walls)
                    if self._sm and not self._boss_bgm_playing:
                        self._boss_bgm_playing = True
                        bgm_map = {
                            1: "asset/Sound/bgm_boss1.wav",
                            2: "asset/Sound/bgm_boss2.wav",
                            3: "asset/Sound/bgm_boss3.wav",
                            4: "asset/Sound/bgm_boss4.wav",
                            5: "asset/Sound/bgm_boss5.wav",
                        }
                        bgm_path = bgm_map.get(self.stage_num, "asset/Sound/bgm_boss1.wav")
                        self._sm.play_bgm(bgm_path)

        # ── 적 업데이트 ──────────────────────────────────
        for e in self.enemies:
            if not e.alive:
                continue
            room_of_e = next((r for r in self.rooms
                              if r.room_idx == getattr(e,'_room_idx',None)), None)
            # 방이 activated(어그로 활성) 상태일 때만 플레이어 추적
            if room_of_e and room_of_e.activated and not room_of_e.cleared:
                result = e.update(p, walls)
            else:
                # 어그로 없음: 타이머만 갱신 (idle)
                result = e.update_idle(walls)
            if result:
                self.e_bullets.append(result)

            # 근접 대미지는 어그로 상태일 때만
            if (room_of_e and room_of_e.activated and not room_of_e.cleared
                    and e.kind in ("slime","bat")):
                dist = math.hypot(p.x-e.x, p.y-e.y)
                if dist < p.radius + e.radius + 2:
                    p.take_damage(e.damage)

        # ── 보스 업데이트 ────────────────────────────────
        if self.boss and not self.boss.is_dead():
            boss_room = next((r for r in self.rooms if r.is_boss), None)
            if boss_room and boss_room.activated and not boss_room.cleared:
                boss_rect   = pygame.Rect(boss_room.px, boss_room.py,
                                          boss_room.rw, boss_room.rh)
                new_bullets = self.boss.update(p, walls, room_rect=boss_rect)
                self.e_bullets.extend(new_bullets)
                # 보스 근접 충돌 (보스가 플레이어에 닿으면 피해)
                if math.hypot(p.x-self.boss.x, p.y-self.boss.y) < p.radius + self.boss.RADIUS + 2:
                    p.take_damage(15)

        # ── 플레이어 탄 (활성화된 방 적에게만) ──────────────
        for b in self.bullets:
            b.update()
            if not b.alive: continue
            for e in self.enemies:
                if not e.alive: continue
                room_of_e = next((r for r in self.rooms
                                  if r.room_idx == getattr(e, '_room_idx', None)), None)
                if not (room_of_e and room_of_e.activated and not room_of_e.cleared):
                    continue
                if b.get_rect().colliderect(e.get_rect()):
                    e.take_damage(b.damage)
                    b.alive = False
                    if not e.alive:
                        gm.score += e.score
                        for _ in range(random.randint(1, 3)):
                            self.coins.append(Coin(
                                e.x + random.randint(-20, 20),
                                e.y + random.randint(-20, 20), 5))
                    break
            if b.alive and self.boss and not self.boss.is_dead():
                boss_room = next((r for r in self.rooms if r.is_boss), None)
                if boss_room and boss_room.activated and not boss_room.cleared:
                    if b.get_rect().colliderect(self.boss.get_rect()):
                        self.boss.take_damage(b.damage)
                        b.alive = False
                        if self.boss.is_dead():
                            gm.score += self.boss.score
                            gm.reroll_tickets += 1   # 보스 처치 → 리롤권 1개 드롭
                            for _ in range(random.randint(5, 8)):
                                self.coins.append(Coin(
                                    self.boss.x + random.randint(-30, 30),
                                    self.boss.y + random.randint(-30, 30), 10))
            if b.alive:
                for w in walls:
                    if b.get_rect().colliderect(w):
                        b.alive = False; break

        # ── 참격 SlashWave (활성화된 방 적에게만) ────────────
        for s in self.slash_effects:
            s.update()
            if not s.alive: continue
            for e in self.enemies:
                if not e.alive: continue
                room_of_e = next((r for r in self.rooms
                                  if r.room_idx == getattr(e, '_room_idx', None)), None)
                if not (room_of_e and room_of_e.activated and not room_of_e.cleared):
                    continue
                if s.get_rect().colliderect(e.get_rect()):
                    e.take_damage(s.damage)
                    s.alive = False
                    if not e.alive:
                        gm.score += e.score
                        for _ in range(random.randint(1, 3)):
                            self.coins.append(Coin(
                                e.x + random.randint(-20, 20),
                                e.y + random.randint(-20, 20), 5))
                    break
            if s.alive and self.boss and not self.boss.is_dead():
                boss_room = next((r for r in self.rooms if r.is_boss), None)
                if boss_room and boss_room.activated and not boss_room.cleared:
                    if s.get_rect().colliderect(self.boss.get_rect()):
                        self.boss.take_damage(s.damage)
                        s.alive = False
                        if self.boss.is_dead():
                            gm.score += self.boss.score
                            gm.reroll_tickets += 1   # 보스 처치 → 리롤권 1개 드롭
                            for _ in range(random.randint(5, 8)):
                                self.coins.append(Coin(
                                    self.boss.x + random.randint(-30, 30),
                                    self.boss.y + random.randint(-30, 30), 10))
            if s.alive:
                for w in walls:
                    if s.get_rect().colliderect(w):
                        s.alive = False; break

        # ── 적 탄 ────────────────────────────────────────
        for b in self.e_bullets:
            b.update()
            if not b.alive: continue
            if b.get_rect().colliderect(p.get_rect()):
                p.take_damage(b.damage); b.alive = False
            for w in walls:
                if b.get_rect().colliderect(w):
                    b.alive = False; break

        self.bullets       = [b for b in self.bullets       if b.alive]
        self.e_bullets     = [b for b in self.e_bullets     if b.alive]
        self.slash_effects = [s for s in self.slash_effects if s.alive]

        # ── 방 클리어 판정 → 문 열림 ─────────────────────
        for room in self.rooms:
            if room.cleared or not room.activated:
                continue
            enemies_dead = len(self._enemies_in_room(room.room_idx)) == 0
            if room.is_boss:
                boss_dead = (self.boss is None or self.boss.is_dead())
                if enemies_dead and boss_dead:
                    room.cleared = True
                    room.locked  = False
                    if not hasattr(self, '_clear_triggered'):
                        self._clear_triggered = True
                        self._start_dice()
                        if self._sm:
                            self._sm.play_bgm("asset/Sound/bgm_main.wav")
                        self._boss_bgm_playing = False
                        gm.state = "ROOM_CLEAR"   # 보스방 클리어 → 주사위 보상
            else:
                if enemies_dead and not room.reward_given:
                    room.cleared      = True
                    room.locked       = False
                    room.reward_given = True
                    # 일정 확률로 상인 등장
                    import random as _r
                    if _r.random() < Merchant.APPEAR_CHANCE:
                        self.merchant.open()
                        gm.pending_merchant = True

        # ── 코인 ─────────────────────────────────────────
        for c in self.coins:
            c.update()
            if c.alive and math.hypot(p.x-c.x, p.y-c.y) < p.radius+12:
                gm.coins += c.value; c.alive = False
        self.coins = [c for c in self.coins if c.alive]

        if p.is_dead():
            gm.state = "GAMEOVER"

    # ── 그리기 ───────────────────────────────────────────

    def draw(self, screen, gm):
        """
        월드(타일·스프라이트)는 ZOOM 뷰포트에 그린 뒤 canvas(screen)로 확대.
        HUD(HP바·스코어·미니맵·방이름)는 canvas에 직접 그려 선명하게 유지.
        """
        sw, sh = screen.get_size()          # canvas 크기 (800x600)
        vw, vh = self.ZOOM_W, self.ZOOM_H   # 뷰포트 크기 (작음 = 줌인)
        cam_x, cam_y = self._get_cam()

        # 월드를 뷰포트(vp)에 그린다
        vp = pygame.Surface((vw, vh))
        vp.fill((20, 16, 32))

        # 바닥
        for (fx, fy, is_boss) in self.floors:
            sx, sy = fx - cam_x, fy - cam_y
            if -TILE < sx < vw + TILE and -TILE < sy < vh + TILE:
                if is_boss:
                    col = C_BOSS_FLOOR if (fx//TILE + fy//TILE) % 2 == 0 else C_BOSS_FLOOR2
                else:
                    col = C_FLOOR      if (fx//TILE + fy//TILE) % 2 == 0 else C_FLOOR2
                pygame.draw.rect(vp, col, (sx, sy, TILE, TILE))

        # 정적 벽
        for w in self.walls:
            r = w.move(-cam_x, -cam_y)
            if r.right < 0 or r.left > vw or r.bottom < 0 or r.top > vh:
                continue
            pygame.draw.rect(vp, C_WALL, r)
            pygame.draw.rect(vp, C_WALL_TOP, pygame.Rect(r.x, r.y, r.w, 6))

        # 문 그리기
        for room in self.rooms:
            for d, dw in self.door_rects[room.room_idx].items():
                r = dw.move(-cam_x, -cam_y)
                if r.right < 0 or r.left > vw or r.bottom < 0 or r.top > vh:
                    continue
                if room.cleared or not room.activated:
                    pygame.draw.rect(vp, C_DOOR_OPEN, r)
                elif room.locked:
                    pygame.draw.rect(vp, C_DOOR_CLOSE, r)
                    pygame.draw.rect(vp, (220, 80, 80), r, 2)
                    remain = len(self._enemies_in_room(room.room_idx))
                    font_d = pygame.font.SysFont(None, 18)
                    dt = font_d.render(f"x{remain}", True, (255, 220, 220))
                    vp.blit(dt, (r.centerx - dt.get_width()//2, r.centery - 7))

        # 문 위 벽 하이라이트
        for room in self.rooms:
            if room.locked:
                for d, dw in self.door_rects[room.room_idx].items():
                    r = dw.move(-cam_x, -cam_y)
                    pygame.draw.rect(vp, C_WALL_TOP, pygame.Rect(r.x, r.y, r.w, 6))

        # 출구
        boss_r = next(r for r in self.rooms if r.is_boss)
        if boss_r.cleared:
            er = self.exit_rect.move(-cam_x, -cam_y)
            pulse = int(abs(math.sin(self._tick * 0.05)) * 40)
            pygame.draw.rect(vp, (60 + pulse, 200 + pulse//2, 120), er, border_radius=4)
            pygame.draw.rect(vp, C_EXIT, er, 3, border_radius=4)
            font_e = pygame.font.SysFont(None, 22)
            et = font_e.render("EXIT", True, (20, 20, 20))
            vp.blit(et, (er.centerx - et.get_width()//2, er.centery - et.get_height()//2))

        # 방 라벨
        font_rl = pygame.font.SysFont(None, 20)
        for room in self.rooms:
            cx, cy = room.center()
            sx, sy = cx - cam_x, cy - cam_y
            if 0 < sx < vw and 0 < sy < vh:
                if room.is_boss:    lbl, col = "BOSS",  (255, 200, 80)
                elif room.is_start: lbl, col = "START", (150, 220, 150)
                else:               lbl, col = f"R{room.room_idx}", (160, 140, 200)
                lt = font_rl.render(lbl, True, col)
                vp.blit(lt, (sx - lt.get_width()//2, sy - room.rh//2 + 4))

        # 코인·적탄·적·보스·플탄·참격·플레이어
        for c in self.coins:         c.draw(vp, cam_x, cam_y)
        for b in self.e_bullets:     b.draw(vp, cam_x, cam_y)
        for e in self.enemies:       e.draw(vp, cam_x, cam_y)
        if self.boss and not self.boss.is_dead():
            self.boss.draw(vp, cam_x, cam_y)
        for b in self.bullets:       b.draw(vp, cam_x, cam_y)
        for s in self.slash_effects: s.draw(vp, cam_x, cam_y)
        self.player.draw(vp, cam_x, cam_y)

        # 뷰포트를 canvas(screen) 크기로 확대
        pygame.transform.scale(vp, (sw, sh), screen)

        # HUD는 canvas에 직접 그려 선명하게 유지
        self.player.draw_hud(screen, sw, sh)
        self._draw_hud(screen, gm, sw, sh)

        cur = self._current_room()
        if cur.is_boss and self.boss and not self.boss.is_dead():
            self.boss.draw_boss_bar(screen, sw)

        if cur.is_boss:
            rname, nc = "BOSS ROOM", (255, 80, 80)
        elif cur.is_start:
            rname, nc = "Start Room", (150, 220, 150)
        else:
            rname, nc = f"Room {cur.room_idx}", (180, 160, 220)
        font_room = pygame.font.SysFont(None, 28)
        rt = font_room.render(rname, True, nc)
        screen.blit(rt, (sw//2 - rt.get_width()//2, 8))

        self._draw_minimap(screen, sw, sh)

    def _draw_hud(self, screen, gm, sw, sh):
        font = pygame.font.SysFont(None,28)
        st = font.render(f"Score: {gm.score}",True,(220,200,100))
        screen.blit(st,(sw-st.get_width()-16,14))
        ct = font.render(f"Coins: {gm.coins}",True,C_COIN)
        screen.blit(ct,(sw-ct.get_width()-16,42))
        ht = pygame.font.SysFont(None,20).render("ESC: Lobby",True,(120,110,140))
        screen.blit(ht,(16,sh-22))

    def _draw_minimap(self, screen, sw, sh):
        """
        미니맵 (우하단):
        - 미방문 방 → 어두운 박스 + '?' 표시
        - 방문 방   → 유형별 색상 (시작=녹색, 보스=빨강, 일반=보라)
        - 클리어    → 더 어두운 색
        - 현재 방   → 노란 테두리 + 밝게
        - 복도      → 방문한 방 사이만 표시
        """
        mm_cell = 16
        mm_pad  = 5
        mm_x    = sw - 10
        mm_y    = sh - 10

        cur    = self._current_room()
        all_gx = [r.grid_x for r in self.rooms]
        all_gy = [r.grid_y for r in self.rooms]
        min_gx, min_gy = min(all_gx), min(all_gy)
        max_gx, max_gy = max(all_gx), max(all_gy)

        span_w = (max_gx - min_gx + 1) * (mm_cell + mm_pad) - mm_pad + 12
        span_h = (max_gy - min_gy + 1) * (mm_cell + mm_pad) - mm_pad + 12

        # 패널 배경
        px = sw - span_w - 10
        py = sh - span_h - 10
        panel = pygame.Surface((span_w, span_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (12, 8, 22, 195),
                         (0, 0, span_w, span_h), border_radius=6)
        pygame.draw.rect(panel, (60, 48, 90, 200),
                         (0, 0, span_w, span_h), 1, border_radius=6)
        screen.blit(panel, (px, py))

        font_q = pygame.font.SysFont(None, 14)

        # 복도 먼저 그리기 (방 아래에 깔림)
        for room in self.rooms:
            rx = px + 6 + (room.grid_x - min_gx) * (mm_cell + mm_pad)
            ry = py + 6 + (room.grid_y - min_gy) * (mm_cell + mm_pad)
            cx_ = rx + mm_cell // 2
            cy_ = ry + mm_cell // 2

            for d in room.open_dirs:
                ddx, ddy = DIRS[d]
                ngx, ngy = room.grid_x + ddx, room.grid_y + ddy
                if (ngx, ngy) not in self.grid:
                    continue
                n_room     = self.grid[(ngx, ngy)]
                r_visited  = room.room_idx   in self._visited_rooms
                n_visited  = n_room.room_idx in self._visited_rooms
                r_cur      = (room.room_idx   == cur.room_idx)
                n_cur      = (n_room.room_idx == cur.room_idx)

                # 양쪽 중 하나라도 방문(또는 현재)이어야 복도 표시
                if not (r_visited or r_cur or n_visited or n_cur):
                    continue

                tx = px + 6 + (ngx - min_gx) * (mm_cell + mm_pad) + mm_cell//2
                ty = py + 6 + (ngy - min_gy) * (mm_cell + mm_pad) + mm_cell//2

                if room.locked and d in room.open_dirs:
                    lc = (180, 60, 60)
                else:
                    lc = (70, 60, 100)
                pygame.draw.line(screen, lc, (cx_, cy_), (tx, ty), 2)

        # 방 그리기
        for room in self.rooms:
            rx = px + 6 + (room.grid_x - min_gx) * (mm_cell + mm_pad)
            ry = py + 6 + (room.grid_y - min_gy) * (mm_cell + mm_pad)

            is_visited = room.room_idx in self._visited_rooms
            is_current = (room.room_idx == cur.room_idx)

            if not is_visited and not is_current:
                # ── 미방문: 어두운 박스 + '?' ──────────────
                pygame.draw.rect(screen, (28, 22, 42),
                                 (rx, ry, mm_cell, mm_cell), border_radius=2)
                pygame.draw.rect(screen, (55, 44, 78),
                                 (rx, ry, mm_cell, mm_cell), 1, border_radius=2)
                q = font_q.render("?", True, (90, 76, 120))
                screen.blit(q, (rx + mm_cell//2 - q.get_width()//2,
                                ry + mm_cell//2 - q.get_height()//2))
            else:
                # ── 방문 or 현재: 유형별 색 ────────────────
                if room.is_start:
                    base_col = (45, 140, 65)
                elif room.is_boss:
                    base_col = (170, 40, 40) if not room.cleared else (80, 25, 25)
                elif room.cleared:
                    base_col = (38, 55, 75)
                else:
                    base_col = (55, 44, 90)

                # 현재 방 밝게
                if is_current:
                    col = tuple(min(255, c + 55) for c in base_col)
                else:
                    col = base_col

                pygame.draw.rect(screen, col,
                                 (rx, ry, mm_cell, mm_cell), border_radius=2)

                # 보스방 B 라벨
                if room.is_boss and not room.cleared:
                    b_lbl = font_q.render("B", True, (255, 130, 130))
                    screen.blit(b_lbl, (rx + mm_cell//2 - b_lbl.get_width()//2,
                                        ry + mm_cell//2 - b_lbl.get_height()//2))

                # 현재 방 노란 테두리
                if is_current:
                    pygame.draw.rect(screen, (255, 230, 60),
                                     (rx, ry, mm_cell, mm_cell), 2, border_radius=2)
                else:
                    pygame.draw.rect(screen, (75, 62, 110),
                                     (rx, ry, mm_cell, mm_cell), 1, border_radius=2)

        # 플레이어 위치 점
        p_rx = px + 6 + (cur.grid_x - min_gx) * (mm_cell + mm_pad) + mm_cell//2
        p_ry = py + 6 + (cur.grid_y - min_gy) * (mm_cell + mm_pad) + mm_cell//2
        pygame.draw.circle(screen, (255, 255, 255), (p_rx, p_ry), 2)
    # ── 인게임 주사위 팝업 ────────────────────────────────

    # 스탯 정의 (key, 이름, 배율, 포맷, 색)
    _SDEFS = [
        ("hp",  "HP",   10,   "+{v} HP",     (220, 80,  80)),
        ("spd", "SPD",  0.10, "+{v:.1f} SPD",(80, 220, 100)),
        ("atk", "ATK",  3,    "+{v} ATK",    (255,200,  60)),
        ("cd",  "CD",   2,    "-{v} tick",   ( 80,160, 255)),
    ]
    _ROLL_TICKS = 18

    def _start_dice(self):
        """새 주사위 롤 시작 (애니메이션 포함)."""
        import random as _r
        for key,*_ in self._SDEFS:
            self._dice_roll[key]    = _r.randint(1, 6)
            self._dice_rolling[key] = self._ROLL_TICKS
            self._dice_show[key]    = _r.randint(1, 6)

    def _apply_dice(self, player):
        """현재 주사위 결과를 플레이어에 즉시 적용."""
        for key, _, scale, *_ in self._SDEFS:
            v = self._dice_roll.get(key, 1)
            if key == "hp":
                player.max_hp += v * int(scale)
                player.hp      = min(player.hp + v * int(scale), player.max_hp)
            elif key == "spd":
                player.speed = round(player.speed + v * scale, 3)
            elif key == "atk":
                player.damage += v * int(scale)
            elif key == "cd":
                player.fire_rate = max(8, player.fire_rate - v * int(scale))

    def _dice_face_surf(self, size, value, color, rolling=False):
        import pygame as _pg
        surf = _pg.Surface((size, size), _pg.SRCALPHA)
        bc   = (255, 255, 180) if rolling else color
        _pg.draw.rect(surf, (30,22,50), (0,0,size,size), border_radius=8)
        _pg.draw.rect(surf, bc,         (0,0,size,size), 3 if rolling else 2, border_radius=8)
        dot_r = max(3, size//10); pad = size//5
        cx, cy = size//2, size//2
        pts = {
            1:[(cx,cy)],
            2:[(pad,pad),(size-pad,size-pad)],
            3:[(pad,pad),(cx,cy),(size-pad,size-pad)],
            4:[(pad,pad),(size-pad,pad),(pad,size-pad),(size-pad,size-pad)],
            5:[(pad,pad),(size-pad,pad),(cx,cy),(pad,size-pad),(size-pad,size-pad)],
            6:[(pad,pad),(size-pad,pad),(pad,cy),(size-pad,cy),(pad,size-pad),(size-pad,size-pad)],
        }
        dc = (255,255,180) if rolling else color
        for px,py in pts.get(max(1,min(6,value)),[]):
            _pg.draw.circle(surf, dc, (px,py), dot_r)
        return surf

    def handle_event(self, event, gm):
        import random as _r
        import pygame as _pg

        # ── ROOM_CLEAR 팝업 이벤트 ──────────────────────
        if gm.state == "ROOM_CLEAR":
            # 주사위 굴림 애니메이션 업데이트
            for key in list(self._dice_rolling):
                if self._dice_rolling[key] > 0:
                    self._dice_rolling[key] -= 1
                    self._dice_show[key] = _r.randint(1, 6)

            if event.type == _pg.MOUSEBUTTONDOWN and event.button == 1:
                # 개별 주사위 클릭 → 해당 주사위 재롤 (티켓 소모)
                for key, dr in self._dice_rects.items():
                    if dr.collidepoint(event.pos):
                        if gm.reroll_tickets > 0:
                            gm.reroll_tickets -= 1
                            self._dice_roll[key]    = _r.randint(1, 6)
                            self._dice_rolling[key] = self._ROLL_TICKS
                            self._dice_show[key]    = _r.randint(1, 6)
                        return

                # CONFIRM 버튼
                if hasattr(self, '_confirm_rect') and self._confirm_rect.collidepoint(event.pos):
                    for key in self._dice_rolling:
                        self._dice_rolling[key] = 0
                    self._apply_dice(self.player)
                    gm.state = "CLEAR"   # 보너스 확정 → 스테이지 클리어
                    return

                # REROLL ALL 버튼
                if hasattr(self, '_reroll_rect') and self._reroll_rect.collidepoint(event.pos):
                    if gm.reroll_tickets > 0:
                        gm.reroll_tickets -= 1
                        self._start_dice()
                    return
            return

        # ── 일반 스테이지 이벤트 ────────────────────────
        if event.type == _pg.MOUSEBUTTONDOWN and event.button == 1:
            cam_x, cam_y = self._get_cam()
            vp_pos = self._canvas_to_vp(event.pos)
            b = self.player.try_shoot(vp_pos, cam_x, cam_y)
            if b:
                if self._sm:
                    self._sm.play_sfx("asset/Sound/sfx_attack.wav")
                if hasattr(b, '_angle'):
                    self.slash_effects.append(b)
                else:
                    self.bullets.append(b)

    def draw_dice_popup(self, screen, gm):
        """방 클리어 후 주사위 보상 팝업 (canvas 위에 직접 그림)."""
        import pygame as _pg
        import random as _r

        sw, sh = screen.get_size()

        # 배경 오버레이
        overlay = _pg.Surface((sw, sh), _pg.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        # 팝업 패널
        pw, ph2 = 420, 360
        px2 = sw//2 - pw//2
        py2 = sh//2 - ph2//2
        panel = _pg.Surface((pw, ph2), _pg.SRCALPHA)
        _pg.draw.rect(panel, (18, 14, 35, 240), (0,0,pw,ph2), border_radius=14)
        _pg.draw.rect(panel, (100, 70, 180, 220), (0,0,pw,ph2), 2, border_radius=14)
        screen.blit(panel, (px2, py2))

        # 제목
        font_t = _pg.font.SysFont(None, 36)
        t = font_t.render("ROOM  CLEAR  —  BONUS!", True, (255, 210, 60))
        screen.blit(t, (sw//2 - t.get_width()//2, py2 + 14))

        # 티켓 수
        font_tk = _pg.font.SysFont(None, 22)
        tkt = font_tk.render(f"Tickets: {gm.reroll_tickets}  (click die to reroll -1)", True, (180, 160, 220))
        screen.blit(tkt, (sw//2 - tkt.get_width()//2, py2 + 46))

        # 주사위 4개
        dice_size = 52
        row_h     = 64
        dy0       = py2 + 76
        font_dl   = _pg.font.SysFont(None, 22)
        self._dice_rects = {}

        for i, (key, name, scale, fmt, col) in enumerate(self._SDEFS):
            row_y   = dy0 + i * row_h
            rolling = self._dice_rolling.get(key, 0) > 0
            dv      = self._dice_show.get(key, 1) if rolling else self._dice_roll.get(key, 1)

            # 이름
            lt = font_dl.render(name, True, col)
            screen.blit(lt, (px2 + 18, row_y + (dice_size - lt.get_height())//2))

            # 주사위
            dx = px2 + 72
            hovered = (_pg.Rect(dx, row_y, dice_size, dice_size).collidepoint(_pg.mouse.get_pos())
                       and gm.reroll_tickets > 0 and not rolling)
            dsurf = self._dice_face_surf(dice_size, dv, col, rolling=rolling or hovered)
            screen.blit(dsurf, (dx, row_y))
            self._dice_rects[key] = _pg.Rect(dx, row_y, dice_size, dice_size)

            # 클릭 힌트
            if hovered:
                ht2 = _pg.font.SysFont(None, 17).render("click!", True, (255,255,180))
                screen.blit(ht2, (dx, row_y - 13))

            # 보너스 수치
            actual = dv * scale
            if key in ("hp","atk","cd"): bonus_str = fmt.format(v=int(actual))
            else:                         bonus_str = fmt.format(v=actual)
            bt = font_dl.render(bonus_str, True, (200,200,200) if rolling else col)
            screen.blit(bt, (dx + dice_size + 14, row_y + (dice_size - bt.get_height())//2))

        # REROLL ALL 버튼
        rw, rh = 150, 34
        rx2 = sw//2 - rw - 8
        ry2 = py2 + ph2 - 52
        self._reroll_rect = _pg.Rect(rx2, ry2, rw, rh)
        rc = (80,50,20) if gm.reroll_tickets > 0 else (40,35,30)
        _pg.draw.rect(screen, rc, self._reroll_rect, border_radius=6)
        _pg.draw.rect(screen, (160,100,40), self._reroll_rect, 2, border_radius=6)
        rt2 = font_dl.render(f"REROLL ALL (1 ticket)", True, (230,180,80) if gm.reroll_tickets>0 else (100,90,70))
        screen.blit(rt2, (self._reroll_rect.centerx - rt2.get_width()//2,
                          self._reroll_rect.centery - rt2.get_height()//2))

        # CONFIRM 버튼
        cw, ch = 150, 34
        cx3 = sw//2 + 8
        cy3 = ry2
        self._confirm_rect = _pg.Rect(cx3, cy3, cw, ch)
        cc = (40,120,60) if not any(v>0 for v in self._dice_rolling.values()) else (30,60,40)
        _pg.draw.rect(screen, cc, self._confirm_rect, border_radius=6)
        _pg.draw.rect(screen, (80,200,100), self._confirm_rect, 2, border_radius=6)
        ct2 = font_dl.render("TAKE BONUS", True, (180,255,180))
        screen.blit(ct2, (self._confirm_rect.centerx - ct2.get_width()//2,
                          self._confirm_rect.centery - ct2.get_height()//2))