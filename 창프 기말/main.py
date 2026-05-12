import pygame

from scripts.game_manager import GameManager

from scripts.stage1 import Stage1

from scripts.player import Player

pygame.init()

screen = pygame.display.set_mode((800,600))

pygame.display.set_caption("Boss Rush")

clock = pygame.time.Clock()

font = pygame.font.SysFont(None, 40)

gm = GameManager()

player = Player()

running = True

stage1 = Stage1()


# 랭킹 저장 함수
def save_ranking(clear_time):

    rankings = []

    try:

        with open("data/ranking.txt", "r") as file:

            for line in file:

                rankings.append(float(line.strip()))

    except:
        pass

    rankings.append(clear_time)

    rankings.sort()

    rankings = rankings[:10]

    with open("data/ranking.txt", "w") as file:

        for rank in rankings:

            file.write(f"{rank}\n")


# 랭킹 불러오기
def load_ranking():

    rankings = []

    try:

        with open("data/ranking.txt", "r") as file:

            for line in file:

                rankings.append(float(line.strip()))

    except:
        pass

    return rankings


saved = False

while running:

    clock.tick(60)

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False

        # 키 입력
        if event.type == pygame.KEYDOWN:

            # 시작 화면
            if gm.state == "START":

                if event.key == pygame.K_SPACE:

                    gm.start_game()

            # 스테이지1 -> 스테이지2
            elif gm.state == "STAGE1":

                if event.key == pygame.K_1:

                    gm.next_stage()

            # 스테이지2 -> 스테이지3
            elif gm.state == "STAGE2":

                if event.key == pygame.K_2:

                    gm.next_stage()

            # 스테이지3 -> 클리어
            elif gm.state == "STAGE3":

                if event.key == pygame.K_3:

                    gm.next_stage()

            # 죽기
            if event.key == pygame.K_q:

                gm.game_over()

    screen.fill((30,30,30))

    # 시작 화면
    if gm.state == "START":

        text = font.render(
            "PRESS SPACE TO START",
            True,
            (255,255,255)
        )

        screen.blit(text, (220,300))

    # 스테이지1
    elif gm.state == "STAGE1":
        
        stage1.update()

        stage1.draw(screen)
        
        player_rect = pygame.Rect(
            player.x,
            player.y,
            player.width,
            player.height
        )

        # 용암 충돌
        for lava in stage1.lavas:

            if player_rect.colliderect(lava):

                player.damage(10)

    # 레이저 충돌
        for laser in stage1.lasers:

            if laser.active:

                if player_rect.colliderect(
                laser.rect
                ):

                    player.damage(5)

        stage_text = font.render(
            "STAGE 1",
            True,
            (255,255,255)
        )

        timer_text = font.render(
            f"TIME : {gm.get_time():.2f}",
            True,
            (255,255,255)
        )

        next_text = font.render(
            "PRESS 1 -> STAGE2",
            True,
            (255,255,255)
        )

        screen.blit(stage_text, (320,200))
        screen.blit(timer_text, (20,20))
        screen.blit(next_text, (250,300))

    # 스테이지2
    elif gm.state == "STAGE2":

        stage_text = font.render(
            "STAGE 2",
            True,
            (255,255,255)
        )

        timer_text = font.render(
            f"TIME : {gm.get_time():.2f}",
            True,
            (255,255,255)
        )

        next_text = font.render(
            "PRESS 2 -> STAGE3",
            True,
            (255,255,255)
        )

        screen.blit(stage_text, (320,200))
        screen.blit(timer_text, (20,20))
        screen.blit(next_text, (250,300))

    # 스테이지3
    elif gm.state == "STAGE3":

        stage_text = font.render(
            "STAGE 3",
            True,
            (255,255,255)
        )

        timer_text = font.render(
            f"TIME : {gm.get_time():.2f}",
            True,
            (255,255,255)
        )

        clear_text = font.render(
            "PRESS 3 -> CLEAR",
            True,
            (255,255,255)
        )

        screen.blit(stage_text, (320,200))
        screen.blit(timer_text, (20,20))
        screen.blit(clear_text, (250,300))

    # 클리어 화면
    elif gm.state == "CLEAR":

        # 기록 저장 한번만
        if not saved:

            save_ranking(gm.clear_time)

            saved = True

        clear_text = font.render(
            "GAME CLEAR",
            True,
            (255,255,255)
        )

        time_text = font.render(
            f"CLEAR TIME : {gm.clear_time:.2f}",
            True,
            (255,255,255)
        )

        screen.blit(clear_text, (280,80))
        screen.blit(time_text, (230,140))

        rankings = load_ranking()

        # 랭킹 출력
        for i in range(10):

            if i < len(rankings):

                text = f"{i+1}. {rankings[i]:.2f}"

            else:

                text = f"{i+1}."

            rank_render = font.render(
                text,
                True,
                (255,255,255)
            )

            screen.blit(
                rank_render,
                (300, 220 + i * 30)
            )

    # 게임오버
    elif gm.state == "GAMEOVER":

        over_text = font.render(
            "GAME OVER",
            True,
            (255,0,0)
        )

        info_text = font.render(
            "TIME NOT SAVED",
            True,
            (255,255,255)
        )

        screen.blit(over_text, (280,260))
        screen.blit(info_text, (240,320))

    pygame.display.update()

pygame.quit()