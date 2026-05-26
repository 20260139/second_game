# scripts/animation.py

class Animation:
    def __init__(self, frames, speed, loop=True):
        self.frames = frames
        self.speed  = speed   # 프레임당 tick 수
        self.loop   = loop
        self.index  = 0
        self.timer  = 0
        self.done   = False   # loop=False 일 때 1사이클 완료 여부

    def update(self):
        if self.done:
            return
        self.timer += 1
        if self.timer >= self.speed:
            self.timer = 0
            self.index += 1
            if self.index >= len(self.frames):
                if self.loop:
                    self.index = 0
                else:
                    self.index = len(self.frames) - 1
                    self.done  = True

    def get_image(self):
        return self.frames[self.index]

    def reset(self):
        self.index = 0
        self.timer = 0
        self.done  = False
