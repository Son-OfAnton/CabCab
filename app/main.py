"""Main functionality for the CabCab application."""

def process_command(command, option=None):
    """
    Process the given command.
    
    Args:
        command (str): Command to process
        option (str, optional): Optional parameter
        
    Returns:
        str: Result of the processed command
    """
    if command == "hello":
        return f"Hello, CabCab! Option: {option or 'None'}"
    else:
        return f"Unknown command: {command}"