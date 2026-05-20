# scripts/stage1.py
"""
소울나이트 스타일 Stage 1 - 확장 맵 버전
- 시작방(고정) + 랜덤 분기 방 구조 (MAX_ROOMS개)
- 평소: 문이 열려 있고 적은 어그로 없음 (idle 배회)
- 방 입장: 문이 닫히고 적이 플레이어를 추적
- 방 클리어: 문이 다시 열림
"""

import pygame, math, random
from scripts.enemy import Enemy
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
        self.cleared   = is_start   # 시작방은 시작부터 클리어
        self.locked    = False      # 어떤 방도 처음엔 열려 있음
        self.activated = is_start   # 한 번이라도 입장했는지 (어그로 트리거)

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

    def __init__(self, player):
        self.player    = player
        self.bullets   = []
        self.e_bullets = []
        self.enemies   = []
        self.coins     = []
        self._tick     = 0
        self.current_room_idx = 0

        self._generate_map()
        self._build_geometry()
        self._spawn_all_enemies()

        cx, cy = self.rooms[0].center()
        player.x = float(cx)
        player.y = float(cy)

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
             (ROOM_W//2-2,ROOM_H//2+1),(ROOM_W//2-1,ROOM_H//2+1),(ROOM_W//2,ROOM_H//2+1),
             (ROOM_W//2-2,ROOM_H//2-1),(ROOM_W//2-2,ROOM_H//2),
             (ROOM_W//2,ROOM_H//2-1),(ROOM_W//2,ROOM_H//2)],
        ]
        for c, r in patterns[room_idx % len(patterns)]:
            self.walls.append(pygame.Rect(ox+c*T, oy+r*T, T, T))

    def _spawn_all_enemies(self):
        T=TILE; RW=ROOM_W*T; RH=ROOM_H*T
        for room in self.rooms:
            if room.is_start:
                continue
            ox, oy = room.px, room.py
            if room.is_boss:
                kinds = ["slime","bat","bat","archer","archer","archer"]
            elif room.room_idx <= 2:
                kinds = random.choices(["slime","slime","bat"], k=3)
            elif room.room_idx <= 4:
                kinds = random.choices(["slime","bat","archer"], k=4)
            else:
                kinds = random.choices(["bat","archer","archer"], k=4)
            for kind in kinds:
                ex = ox + T*2 + random.randint(0, RW-T*4)
                ey = oy + T*2 + random.randint(0, RH-T*4)
                e = Enemy(ex, ey, kind)
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

    def _get_cam(self):
        sw, sh = 800, 600
        p = self.player
        return int(p.x)-sw//2, int(p.y)-sh//2

    # ── 이벤트 ───────────────────────────────────────────

    def handle_event(self, event, gm):
        p = self.player
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cam_x, cam_y = self._get_cam()
            b = p.try_shoot(event.pos, cam_x, cam_y)
            if b:
                self.bullets.append(b)

    # ── 업데이트 ─────────────────────────────────────────

    def update(self, keys, mouse_pos, gm):
        self._tick += 1
        p     = self.player
        walls = self._current_walls()
        cam_x, cam_y = self._get_cam()

        p.handle_input(keys, mouse_pos, walls, cam_x, cam_y)
        p.update()

        cur_room = self._current_room()
        self.current_room_idx = cur_room.room_idx

        # ── 방 입장 감지 → 문 잠금 + 어그로 활성화 ──────
        for room in self.rooms:
            if room.is_start or room.cleared or room.activated:
                continue
            # 플레이어가 방 내부(벽 안쪽)에 완전히 들어왔을 때
            if room.inner_rect().collidepoint(p.x, p.y):
                room.activated = True
                room.locked    = True   # 문 닫힘

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

        # ── 플레이어 탄 ──────────────────────────────────
        for b in self.bullets:
            b.update()
            if not b.alive: continue
            for e in self.enemies:
                if not e.alive: continue
                if b.get_rect().colliderect(e.get_rect()):
                    e.take_damage(b.damage)
                    b.alive = False
                    if not e.alive:
                        gm.score += e.score
                        for _ in range(random.randint(1,3)):
                            self.coins.append(Coin(
                                e.x+random.randint(-20,20),
                                e.y+random.randint(-20,20), 5))
                    break
            for w in walls:
                if b.get_rect().colliderect(w):
                    b.alive = False; break

        # ── 적 탄 ────────────────────────────────────────
        for b in self.e_bullets:
            b.update()
            if not b.alive: continue
            if b.get_rect().colliderect(p.get_rect()):
                p.take_damage(b.damage); b.alive = False
            for w in walls:
                if b.get_rect().colliderect(w):
                    b.alive = False; break

        self.bullets   = [b for b in self.bullets   if b.alive]
        self.e_bullets = [b for b in self.e_bullets if b.alive]

        # ── 방 클리어 판정 → 문 열림 ─────────────────────
        for room in self.rooms:
            if room.cleared or not room.activated:
                continue
            if len(self._enemies_in_room(room.room_idx)) == 0:
                room.cleared = True
                room.locked  = False   # 문 열림

        # ── 코인 ─────────────────────────────────────────
        for c in self.coins:
            c.update()
            if c.alive and math.hypot(p.x-c.x, p.y-c.y) < p.radius+12:
                gm.coins += c.value; c.alive = False
        self.coins = [c for c in self.coins if c.alive]

        # ── 출구 판정 ────────────────────────────────────
        boss = next(r for r in self.rooms if r.is_boss)
        if boss.cleared and p.get_rect().colliderect(self.exit_rect):
            gm.state = "CLEAR"

        if p.is_dead():
            gm.state = "GAMEOVER"

    # ── 그리기 ───────────────────────────────────────────

    def draw(self, screen, gm):
        sw, sh = screen.get_size()
        cam_x, cam_y = self._get_cam()
        screen.fill((20,16,32))

        # 바닥
        for (fx, fy, is_boss) in self.floors:
            sx, sy = fx-cam_x, fy-cam_y
            if -TILE < sx < sw+TILE and -TILE < sy < sh+TILE:
                if is_boss:
                    col = C_BOSS_FLOOR if (fx//TILE+fy//TILE)%2==0 else C_BOSS_FLOOR2
                else:
                    col = C_FLOOR     if (fx//TILE+fy//TILE)%2==0 else C_FLOOR2
                pygame.draw.rect(screen, col, (sx,sy,TILE,TILE))

        # 정적 벽
        for w in self.walls:
            r = w.move(-cam_x, -cam_y)
            if r.right<0 or r.left>sw or r.bottom<0 or r.top>sh: continue
            pygame.draw.rect(screen, C_WALL, r)
            pygame.draw.rect(screen, C_WALL_TOP, pygame.Rect(r.x,r.y,r.w,6))

        # 문 그리기
        for room in self.rooms:
            for d, dw in self.door_rects[room.room_idx].items():
                r = dw.move(-cam_x, -cam_y)
                if r.right<0 or r.left>sw or r.bottom<0 or r.top>sh: continue

                if room.cleared or not room.activated:
                    # 열린 문: 바닥색으로 채워서 통로처럼 보임
                    pygame.draw.rect(screen, C_DOOR_OPEN, r)
                elif room.locked:
                    # 닫힌 문: 빨간색 + 남은 적 수 표시
                    pygame.draw.rect(screen, C_DOOR_CLOSE, r)
                    pygame.draw.rect(screen, (220,80,80), r, 2)
                    remain = len(self._enemies_in_room(room.room_idx))
                    font_d = pygame.font.SysFont(None, 18)
                    dt = font_d.render(f"×{remain}", True, (255,220,220))
                    screen.blit(dt, (r.centerx-dt.get_width()//2, r.centery-7))

        # 문 위에 벽 상단 하이라이트 (locked 문을 벽처럼 보이게)
        for room in self.rooms:
            if room.locked:
                for d, dw in self.door_rects[room.room_idx].items():
                    r = dw.move(-cam_x, -cam_y)
                    pygame.draw.rect(screen, C_WALL_TOP, pygame.Rect(r.x,r.y,r.w,6))

        # 출구
        boss = next(r for r in self.rooms if r.is_boss)
        if boss.cleared:
            er = self.exit_rect.move(-cam_x, -cam_y)
            pulse = int(abs(math.sin(self._tick*0.05))*40)
            pygame.draw.rect(screen, (60+pulse, 200+pulse//2, 120), er, border_radius=4)
            pygame.draw.rect(screen, C_EXIT, er, 3, border_radius=4)
            font_e = pygame.font.SysFont(None,22)
            et = font_e.render("EXIT", True, (20,20,20))
            screen.blit(et,(er.centerx-et.get_width()//2, er.centery-et.get_height()//2))

        # 방 라벨
        font_rl = pygame.font.SysFont(None,20)
        for room in self.rooms:
            cx,cy = room.center()
            sx,sy = cx-cam_x, cy-cam_y
            if 0<sx<sw and 0<sy<sh:
                if room.is_boss:   lbl,col = "BOSS",(255,200,80)
                elif room.is_start:lbl,col = "START",(150,220,150)
                else:              lbl,col = f"R{room.room_idx}",(160,140,200)
                lt = font_rl.render(lbl,True,col)
                screen.blit(lt,(sx-lt.get_width()//2, sy-room.rh//2+4))

        # 코인 / 적탄 / 적 / 플탄 / 플레이어
        for c in self.coins:        c.draw(screen, cam_x, cam_y)
        for b in self.e_bullets:    b.draw(screen, cam_x, cam_y)
        for e in self.enemies:      e.draw(screen, cam_x, cam_y)
        for b in self.bullets:      b.draw(screen, cam_x, cam_y)
        self.player.draw(screen, cam_x, cam_y)

        self.player.draw_hud(screen, sw, sh)
        self._draw_hud(screen, gm, sw, sh)

        # 방 이름 (상단 중앙)
        cur = self._current_room()
        if cur.is_boss:
            rname,nc = "⚔  BOSS ROOM",(255,80,80)
        elif cur.is_start:
            rname,nc = "Start Room",(150,220,150)
        else:
            rname,nc = f"Room {cur.room_idx}",(180,160,220)
        font_room = pygame.font.SysFont(None,28)
        rt = font_room.render(rname,True,nc)
        screen.blit(rt,(sw//2-rt.get_width()//2,8))

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
        mm_x, mm_y = sw-162, sh-132
        mm_cell, mm_pad = 18, 4
        pygame.draw.rect(screen,(15,12,28),(mm_x-6,mm_y-6,158,128),border_radius=6)
        pygame.draw.rect(screen,(60,50,90),(mm_x-6,mm_y-6,158,128),1,border_radius=6)

        cur     = self._current_room()
        all_gx  = [r.grid_x for r in self.rooms]
        all_gy  = [r.grid_y for r in self.rooms]
        min_gx, min_gy = min(all_gx), min(all_gy)

        for room in self.rooms:
            rx = mm_x + (room.grid_x-min_gx)*(mm_cell+mm_pad)
            ry = mm_y + (room.grid_y-min_gy)*(mm_cell+mm_pad)

            if room.is_boss:
                col = (200,60,60) if not room.cleared else (100,30,30)
            elif room.is_start:
                col = (60,160,80)
            elif room.cleared:
                col = (50,180,90)
            elif room.activated:
                col = (160,80,40)
            else:
                col = (60,50,100)

            pygame.draw.rect(screen, col, (rx,ry,mm_cell,mm_cell), border_radius=3)
            if room == cur:
                pygame.draw.rect(screen,(255,240,80),(rx,ry,mm_cell,mm_cell),2,border_radius=3)

            for d in room.open_dirs:
                dx,dy = DIRS[d]
                nx,ny = room.grid_x+dx, room.grid_y+dy
                if (nx,ny) in self.grid:
                    tx = rx+mm_cell//2+dx*(mm_cell//2+mm_pad//2)
                    ty = ry+mm_cell//2+dy*(mm_cell//2+mm_pad//2)
                    lc = (220,80,80) if room.locked else (80,70,120)
                    pygame.draw.line(screen,lc,(rx+mm_cell//2,ry+mm_cell//2),(tx,ty),2)
