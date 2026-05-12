import time


class GameManager:

    def __init__(self):

        self.state = "START"

        # 게임 시작 시간
        self.start_time = 0

        # 클리어 시간
        self.clear_time = 0

        # 클리어 여부
        self.is_clear = False

    def start_game(self):

        self.state = "STAGE1"

        self.start_time = time.time()

    def next_stage(self):

        if self.state == "STAGE1":

            self.state = "STAGE2"

        elif self.state == "STAGE2":

            self.state = "STAGE3"

        elif self.state == "STAGE3":

            self.game_clear()

    def game_clear(self):

        self.state = "CLEAR"

        self.is_clear = True

        self.clear_time = time.time() - self.start_time

    def game_over(self):

        self.state = "GAMEOVER"

    def get_time(self):

        if self.is_clear:

            return self.clear_time

        return time.time() - self.start_time