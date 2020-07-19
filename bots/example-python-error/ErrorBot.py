class ErrorBot:
    def __init__(self):
        pass

    def make_move(self, gamestate):
        if len(gamestate["rounds"]) > 5:
            raise RuntimeError("Bot failed, lmao")

        return "R"
