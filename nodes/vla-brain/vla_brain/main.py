"""Main entry point for the VLA-Brain node."""

from dora import Node
from vla_op import Operator


def main():
    """Run the VLA inference node using SmolVLA."""
    node = Node()
    # Load model and processors on startup
    brain = Operator()

    for event in node:
        # Handle 'image' input and send 'action' output
        status = brain.on_event(event, node.send_output)
        
        if status.value == "STOP":
            break


if __name__ == "__main__":
    main()