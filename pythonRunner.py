# Usage: pythonRunner.py [file] [port]

import sys, os, importlib, inspect, socket, traceback

if len(sys.argv) < 3 or sys.argv[1] in ["-h", "--help"]:
    print(f"Usage: {sys.argv[0]} [file] [port]")
    sys.exit(0)

bot_file = sys.argv[1]
if not os.path.exists(bot_file):
    print(f"Can't find file {bot_file}")
    sys.exit(1)

print(f"Running file {bot_file}")

module = importlib.import_module(bot_file[:-3].replace("/", "."))

# Looking for a name without a double underscore
possible_bots = []
for name in dir(module):
    if name.startswith("__"): continue
    attr = getattr(module, name)
    if hasattr(attr, "make_move") and inspect.isclass(attr):
        print(f"Found class {name} with make_move")
        possible_bots.append(attr)

if len(possible_bots) > 1:
    print("No support for multiple bots run at the same time yet, please only define one bot per file")
    sys.exit(1)

bot_cls = possible_bots[0]
port = int(sys.argv[2])
print(f"Using {bot_cls.__module__}.{bot_cls.__name__}")
print(f"Connecting on port :{port}")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("localhost", port))
except:
    print("Failed to connect to port")
    sys.exit(1)

# Instantiate, run, make sure no crashes
try:
    bot_instance = bot_cls()
    gamestate = {"rounds": []}
    while True:
        try:
            p1move = bot_instance.make_move(gamestate)
            sock.send(f"{p1move}\n".encode())
            p2move = sock.recv(2).decode("UTF-8")
            if len(p2move) == 0: break
            p2move = p2move[0]
            if p2move in ["E"]:
                print("Opposing bot threw an error, we win")
                break
            gamestate["rounds"].append({"p1":p1move, "p2":p2move})
        except EOFError:
            # Stop
            break
except Exception as ex:
    # Possible bot crash
    print("Error: bot crash")
    print(traceback.format_exc())
    sock.send("E\n".encode())
finally:
    sock.close()
