import random

class DynamiteOnDraw:
    def __init__(self):
        self.dynamite_left = 100
        self.draws = 0

    def make_safe(self, move):
        if move == "D": self.dynamite_left -= 1
        else: return move
        if self.dynamite_left > 0: return move
        return random.choice("RPS")

    def make_move(self, gamestate):
        rounds = gamestate["rounds"]
        if len(rounds) and rounds[-1]["p1"] == rounds[-1]["p2"]:
            self.draws += 1
        else:
            self.draws = 0
            return random.choice(list("RPS"))

        # game of 2500
        # ~667 the same
        if self.draws == 1:
            return self.make_safe(random.choice("RPSD"))
        elif self.draws == 2:
            return self.make_safe(random.choice("RPSDDD"))
        else:
            return self.make_safe("D")

