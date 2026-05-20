# scripts/game_manager.py

class GameManager:
    def __init__(self):
        # LOBBY / STAGE1 / GAMEOVER / CLEAR
        self.state = "LOBBY"
        self.score = 0
        self.coins = 0   # 로비에서 업그레이드 재화
