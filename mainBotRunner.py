import sys, socket, subprocess, glob, re, os
from itertools import combinations, product

from concurrent.futures import ThreadPoolExecutor

class ProgressBar:
    def __init__(self, max_n, width, text):
        self.upto = max_n
        self.width = width
        self.text = text
        self.current = 0
        self.show()

    def next(self):
        self.current += 1
        self.show()
    def set_text(self, t):
        self.text = t

    def show(self):
        progress = self.current / self.upto
        bar_w = self.width - len(self.text) - 4 # [=] txt
        bar = ("=" * int(progress * bar_w)).ljust(bar_w, " ")
        print(f"\r[{bar}] {self.text}", end="")
    def done(self):
        print()

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
            ".js": ["node", "jsRunner.js"],
            ".jar": ["java", "-jar", "javaRunner.jar"]
    }

    def __init__(self, bot):
        # Make a server, connect to it
        self.bot_path = bot
        self.type = self.bot_path[self.bot_path.rfind("."):]
        self.bot_name = bot[bot.rfind("/")+1:bot.rfind(".")] + f"({self.type})"
        self.play_round = lambda x: "E"

    def start(self):
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
        try: self.sock.send("E\n")
        except: pass
        self.sock.close()
        stdout = self.bot_process.stdout.read().decode("utf-8")
        self.bot_process.wait()
        return stdout

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
                    self.reason += ": bot1 err"
                    return (0, self.WIN_SCORE)
                self.reason += ": bot2 err"
                return (self.WIN_SCORE, 0)
            self.history.append(self.last_round)
            # Update scores and stuff
            dynamites[0] += p1m == "D"
            dynamites[1] += p2m == "D"
            if (not self.beats(p1m, p2m)) and (not self.beats(p2m, p1m)):
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

class Tournament:
    LOG_DIR = "tournament/"
    def __init__(self, bot_paths, n_games=1):
        self.bots = bot_paths
        self.n_games = n_games
        self.print_bot_info()
        self.games = list(combinations(self.bots, 2))
        self.num_games = int(len(self.bots) * (len(self.bots)-1) / 2)

        if not os.path.exists(self.LOG_DIR):
            os.mkdir(self.LOG_DIR)

    def print_bot_info(self):
        print(f"Tounament, {self.n_games} games each")
        print("="*20)
        for bot in self.bots:
            r = Runner(bot) # Don't start, don't need to actually run
            print(f" * Bot {r.bot_name}")
    
    def play_game(self, game, j):
        bot1, bot2 = map(lambda path: Runner(path), game)
        bot1.start(); bot2.start()
        #print(f"Running game #{i+1}/{self.num_games} - {bot1.bot_name} vs {bot2.bot_name}")
        game_id = self.LOG_DIR + bot1.bot_name + "-" + bot2.bot_name
        match = Match(bot1, bot2)
        score = match.play_game()
        #print(f" #{j+1}/{self.n_games} score: {score}")
        with open(game_id + "-" + str(j) + ".json", "w+") as f:
            save_json(f, match.history)
        with open(game_id + "-" + str(j) + ".log", "w+") as f:
            print(match.reason, file=f)
            print("="*20, file=f)
            print(f"==Bot {bot1.bot_name} output==", file=f)
            print("="*20, file=f)
            print(bot1.quit(), end="", file=f)
            print("="*20, file=f)
            print(f"==Bot {bot2.bot_name} output==", file=f)
            print("="*20, file=f)
            print(bot2.quit(), end="", file=f)
            print("="*20, file=f)
        #print(f" saved to {game_id}.json")
        return score, match.reason

    def play(self):
        print()
        all_games = list(product(self.games, range(self.n_games)))
        #with ThreadPoolExecutor(max_workers = 8) as executor:
        lbots, rbots = zip(*self.games)
        ljust = max(map(lambda b: len(Runner(b).bot_name), lbots))
        rjust = max(map(lambda b: len(Runner(b).bot_name), rbots))
        if True:
            exec_map = map#executor.map
            pbar = ProgressBar(self.num_games * self.n_games, 80, "")
            pbar.show()

            results = \
                list(exec_map(lambda x: [self.play_game(x[0], x[1]), pbar.next()][0],
                    all_games))

        pbar.done()
        botscores = {}
        bottotals = {}
        for (score, reason), (game, n) in zip(results, all_games):
            b1, b2 = map(lambda p: Runner(p), game)
            print(f"{b1.bot_name.rjust(ljust)} v {b2.bot_name.ljust(rjust)}", end="")
            print(f" #{n} : {score} ".ljust(20) + f"- {reason}")
            botscores[b1.bot_name] = botscores.get(b1.bot_name, 0) + (1 if score[0] > score[1] else 0)
            botscores[b2.bot_name] = botscores.get(b2.bot_name, 0) + (1 if score[0] < score[1] else 0)
            bottotals[b1.bot_name] = bottotals.get(b1.bot_name, 0) + score[0]
            bottotals[b2.bot_name] = bottotals.get(b2.bot_name, 0) + score[1]
        print("="*20)
        for i, (name, score) in enumerate(sorted(botscores.items(), key=lambda i: -i[1] - bottotals[i[0]]/(self.n_games*2000))):
            print(f" {i+1}) {name.rjust(max(ljust, rjust))} - {score} - total {bottotals[name]}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} [-n games] [bot1] [bot2] ...")
        sys.exit(0)
    games_specified = sys.argv[1] in ["-n", "--number"]
    num_games = int(sys.argv[2]) if games_specified else 1
    bot_names = sys.argv[(3 if games_specified else 1):]

    bots = list(map(fuzzy_find_bot, bot_names))

    tournament = Tournament(bots, num_games)

    tournament.play()
