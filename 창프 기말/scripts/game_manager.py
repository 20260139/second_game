# scripts/game_manager.py

class GameManager:
    def __init__(self):
        # LOBBY / STAGE1 / GAMEOVER / CLEAR
        self.state          = "LOBBY"
        self.score          = 0
        self.coins          = 0
        self.reroll_tickets = 0   # 리롤권 (보스 처치 드롭 / 코인 구매)
