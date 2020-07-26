import sys, socket, subprocess, glob, re

def get_all_bots():
    # Get list of all bots
    # Looking for items in bots/*/[xxx].py/.js
    # Also bots/*/**.jar (minus helpers)
    ignore_list = ["javarunner", "Runner-Java", "gradle-wrapper"]
    python_bots = glob.glob("bots/*/*.py")
    js_bots = glob.glob("bots/*/*.js")
    jar_files = glob.glob("bots/**/*.jar", recursive=True)
    java_bots = [f for f in jar_files if not any(ignore in f for ignore in ignore_list)]
    return python_bots + js_bots + java_bots

def fuzzy_find_bot(name):
    bots = get_all_bots()
    suggestions = []
    pattern = ".*?".join(char for char in name)
    regex = re.compile(pattern, re.IGNORECASE)
    for bot in bots:
        match = regex.search(bot)
        if match: suggestions.append((len(match.group()), match.start(), bot))
    if len(suggestions) == 0:
        raise RuntimeError(f"Couldn't find bot matching {name}")
    return sorted(suggestions)[0][2]

class Runner:
    EXT_HANDLERS = {
            ".py": ["python3", "pythonRunner.py"],
            ".js": ["node", "jsRunner.js"]
    }

    def __init__(self, bot):
        # Make a server, connect to it
        self.bot_path = bot
        self.bot_name = bot[bot.rfind("/")+1:bot.rfind(".")]
        self.setup_port()
        self.sock_srv.listen(1)
        self.start_bot_client()
        self.sock = self.sock_srv.accept()[0]
        self.play_round = lambda last_move: self._play_round(last_move)

    def setup_port(self):
        self.port = 8001
        self.sock_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while 1:
            try:
                self.sock_srv.bind(("localhost", self.port))
                break
            except OSError: ## Address already in use
                self.port += 1

    def start_bot_client(self):
        self.type = self.bot_path[self.bot_path.rfind("."):]
        if not self.type in Runner.EXT_HANDLERS:
            raise RuntimeError(f"Cannot handle extension {self.type}")
        runner = Runner.EXT_HANDLERS[self.type]
        cmd = runner + [
            self.bot_path,
            str(self.port)
        ]
        self.bot_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def _play_round(self, prev_round=None):
        if prev_round is not None:
            prev_round_char = prev_round[0] ## Make sure
            try: self.sock.send(f"{prev_round_char}\n".encode("utf-8"))
            except:
                self.play_round = lambda x: "E"
                self.sock.close()
                return "E"
        try:
            this_move = ""
            this_move = self.sock.recv(2).decode("utf-8")
        except: pass
        if len(this_move) == 0: # Have an error
            self.play_round = lambda x: "E"
            self.sock.close()
            return "E"
        return this_move[0]

    def quit(self):
        self.sock.close()
        self.bot_process.wait()
        return self.bot_process.stdout.read().decode("utf-8")

class Match:
    GAME_ROUNDS = 2500
    WIN_SCORE = 1000
    NUM_DYNAMITE = 100

    def __init__(self, bot1, bot2):
        self.bot1 = bot1
        self.bot2 = bot2
        self.last_round = [None, None]
        self.history = []
        self.reason = "Game not finished"

    @staticmethod
    def beats(move1, move2):
        return (move1, move2) in [
                ("R", "S"), ("S", "P"), ("P", "R"),
                ("D", "S"), ("D", "P"), ("D", "R"),
                ("W", "D")]

    def play_game(self):
        # Play bots against each other
        scores = [0, 0]
        dynamites = [0, 0]
        round = 0
        round_score = 1

        while max(scores) < self.WIN_SCORE and max(dynamites) <= self.NUM_DYNAMITE and round < self.GAME_ROUNDS and round_score <= self.GAME_ROUNDS:
            # Play round
            p1m = self.bot1.play_round(self.last_round[1])
            p2m = self.bot2.play_round(self.last_round[0])
            self.last_round = [p1m, p2m]
            if "E" in self.last_round:
                self.reason = "Generic error, check bot logs"
                if p1m == "E":
                    return (self.WIN_SCORE, 0)
                return (0, self.WIN_SCORE)
            self.history.append(self.last_round)
            # Update scores and stuff
            dynamites[0] += p1m == "D"
            dynamites[1] += p2m == "D"
            if (not self.beats(p1m, p2m)) and (not self.beats(p1m, p2m)):
                round_score += 1
            elif self.beats(p1m, p2m):
                scores[0] += round_score
                round_score = 1
            else:
                scores[1] += round_score
                round_score = 1
        if max(dynamites) > self.NUM_DYNAMITE: self.reason = "Ran out of dynamite"
        if dynamites[0] > self.NUM_DYNAMITE: return (0, self.WIN_SCORE)
        if dynamites[1] > self.NUM_DYNAMITE: return (self.WIN_SCORE, 0)

        self.reason = "Game finished normally"
        return tuple(scores) 

def save_json(f, history):
    f.write("""{"moves":[""")
    
    f.write(",".join(f"{{\"p1\":\"{m1}\",\"p2\":\"{m2}\"}}" for m1, m2 in history))

    f.write("""]}""")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} [bot1] [bot2]")
        sys.exit(0)
    bot1 = fuzzy_find_bot(sys.argv[1])
    bot2 = fuzzy_find_bot(sys.argv[2])
    match = Match(Runner(bot1), Runner(bot2))
    print(f"Bot {match.bot1.bot_name} running on port {match.bot1.port}")
    print(f"Bot {match.bot2.bot_name} running on port {match.bot2.port}")

    score = match.play_game()

    print(f"Game ended, score = {score}")
    print(f"Reason: {match.reason}")
    print(f"Bot {match.bot1.bot_name} output")
    print("="*20)
    print(match.bot1.quit(), end="")
    print(f"Bot {match.bot2.bot_name} output")
    print("="*20)
    print(match.bot2.quit(), end="")

    save_json(open("results.json", "w+"), match.history)
    print("Saved results to results.json")
