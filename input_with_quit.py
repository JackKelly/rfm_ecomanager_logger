class Quit(Exception):
    """Simple exception class raised when user hits q"""


def input_with_quit(string=""):
    response = raw_input(string)
    if response == "c":
        print("\ncancel\n")
        raise Quit()
    else:
        return response