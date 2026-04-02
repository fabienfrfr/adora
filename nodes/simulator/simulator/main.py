"""Main entry point for the simulator node."""

import pyarrow as pa
from dora import Node
from simulation_op import Operator


def main():
    """Run the genesis-world simulation node."""
    node = Node()
    # Initialize the genesis-world engine
    simulator = Operator()

    for event in node:
        # Delegate event handling to the Operator class
        # This handles 'tick' for rendering and 'action' for motor control
        status = simulator.on_event(event, node.send_output)
        
        if status.value == "STOP":
            break


if __name__ == "__main__":
    main()