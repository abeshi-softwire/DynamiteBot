const {resolve} = require('path');
const net = require('net');

var args = process.argv.slice(2)
if (args.length < 2 || args.includes('-h') || args.includes('--help')) {
  console.log('Usage: ' + process.argv[1] + ' [file] [port]');
  process.exit(1);
}

// Load from given file
bot_file = args[0];
console.log('Running file ' + bot_file);
var bot_instance;
try {
  bot_instance = require(resolve(bot_file));
} catch (e) {
  console.log('Error loading file');
  console.log(e);
  process.exit(1);
}
if (!Object.getOwnPropertyNames(Object.getPrototypeOf(bot_instance))
         .filter(function(e, i, arr) {
           return typeof bot_instance[e] == 'function'
         })
         .includes('makeMove')) {
  console.log('No bot found, please make sure `module.exports = new Bot();`');
  console.log(' and that `makeMove(gamestate)` is defined.');
  process.exit(1);
}

console.log('Using "' + bot_instance.constructor.name + '"');
const port = parseInt(args[1], 10);
if (isNaN(port)) {
  console.log('Error: port ' + args[1] + ' not a number');
  process.exit(1);
}
console.log('Connecting on port ' + port);
var sock;
try {
  sock = new net.Socket();
  sock.connect(port);
} catch (e) {
  console.log('Failed to connect to port');
  process.exit(1);
}

try {
  gamestate = {'rounds': []};
  var p1move = bot_instance.makeMove(gamestate);
  sock.write(p1move + '\n');
  sock.on('data', d => {
    const p2move = String.fromCharCode(d[0]);
    gamestate['rounds'].push({'p1': p1move, 'p2': p2move});
    p1move = bot_instance.makeMove(gamestate);
    sock.write(p1move + '\n');
  });
  sock.on('close', err => {
    sock.end();
  });
} catch (e) {
  // Bot crash, maybe
  console.log('Error: ');
  console.log(e);
}
