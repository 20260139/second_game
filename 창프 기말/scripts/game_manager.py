# scripts/game_manager.py

class GameManager:
    def __init__(self):
        self.state          = "LOBBY"
        self.score          = 0
        self.coins          = 0
        self.reroll_tickets = 0
        self.stage          = 1   # 현재 스테이지 (1~5)
