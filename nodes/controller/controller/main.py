"""Improved Controller node with large xterm window."""

import os
import subprocess
import shutil
import pyarrow as pa
from dora import Node

def main():
    node = Node()
    pipe_path = "/tmp/adora_pipe"
    
    # Setup pipe
    if os.path.exists(pipe_path):
        os.remove(pipe_path)
    os.mkfifo(pipe_path)

    # Shell script with clear instructions
    shell_cmd = (
        'echo "================================"; '
        'echo "   ADORA REMOTE CONTROL"; '
        'echo "================================"; '
        'echo "Commands: Turn left, Turn right, Stop, Go fast..."; '
        'echo ""; '
        'while true; do '
        '  printf "👉 ENTER COMMAND: "; '
        '  read cmd; '
        '  echo "$cmd" > ' + pipe_path + '; '
        'done'
    )

    terminal = shutil.which("xterm")
    if not terminal:
        print("❌ xterm not found.")
        return

    # Configuration de xterm :
    # -geometry 80x20 : Largeur x Hauteur
    # -fa 'Monospace' -fs 12 : Police et Taille
    # -bg black -fg white : Couleurs
    subprocess.Popen([
        terminal, 
        "-T", "Adora Controller",
        "-geometry", "80x20",
        "-fa", "Monospace",
        "-fs", "12",
        "-bg", "black",
        "-fg", "white",
        "-e", "bash", "-c", shell_cmd
    ])

    print("🚀 Control terminal opened (Large version).")

    # Read from pipe
    try:
        while True:
            with open(pipe_path, "r") as fifo:
                for line in fifo:
                    command = line.strip()
                    if command:
                        print(f"🧠 Forwarding: {command}")
                        node.send_output("instruction", pa.array([command]))
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        if os.path.exists(pipe_path):
            os.remove(pipe_path)

if __name__ == "__main__":
    main()