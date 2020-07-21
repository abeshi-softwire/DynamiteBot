import sys, socket, subprocess

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
        ext = self.bot_path[self.bot_path.rfind("."):]
        if not ext in Runner.EXT_HANDLERS:
            raise RuntimeError(f"Cannot handle extension {ext}")
        runner = Runner.EXT_HANDLERS[ext]
        cmd = runner + [
            self.bot_path,
            str(self.port)
        ]
        self.bot_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def play_round(self, prev_round=None):
        if prev_round is not None:
            prev_round_char = prev_round[0] ## Make sure
            self.sock.send(f"{prev_round_char}\n".encode("utf-8"))
        this_move = self.sock.recv(2).decode("utf-8")
        return this_move[0]

    def quit(self):
        self.sock.close()
        self.bot_process.wait()
        return self.bot_process.stdout.read()



if __name__ == "__main__":
    r = Runner("/home/abel/Softwire/DynamiteBot/bots/example-js/rockBot.js")
    print(f"Bot {r.bot_name} running on port {r.port}")

    prev_round = None
    for rnd in range(10):
        print(f"Round {rnd}")
        p1_move = r.play_round(prev_round)
        p2_move = prev_round if prev_round else "D"
        print(f"{p1_move} {p2_move}")
        prev_round = p1_move

