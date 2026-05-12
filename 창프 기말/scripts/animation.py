# animation.py

class Animation:

    def __init__(self, frames, speed):

        self.frames = frames

        self.speed = speed

        self.index = 0

        self.timer = 0

    def update(self):

        self.timer += 1

        if self.timer >= self.speed:

            self.timer = 0

            self.index += 1

            if self.index >= len(self.frames):

                self.index = 0

    def get_image(self):

        return self.frames[self.index]

    def reset(self):

        self.index = 0
        self.timer = 0