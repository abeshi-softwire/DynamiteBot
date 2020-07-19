# Set up server to connect two runners on two ports

port1=8001
port2=8002

out1=record_1.txt
out2=record_2.txt

echo "Launch the runners on ports $port1 and $port2"
echo "Output for each respectively in $out1 and $out2"

rm pipe || true
mkfifo pipe

cat pipe | tee $out1 | nc -lN $port2 | tee $out2 | nc -lN $port1 >pipe
