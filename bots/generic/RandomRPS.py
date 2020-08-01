import random

class RandomRPS:
    def __init__(self):
        pass
    def make_move(self, gamestate):
        return random.choice(["R", "P", "S"])
