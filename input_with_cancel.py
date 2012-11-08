class Cancel(Exception):
    """Simple exception class raised when user hits q"""


def input_with_cancel(string=""):
    response = raw_input(string)
    if response == "c":
        raise Cancel("c key pressed. Cancel command.")
    else:
        return response


def input_int_with_cancel(string=""):
    retries = 0
    while retries < 5:
        response = input_with_cancel(string)
        try:
            return int(response)
        except ValueError:
            print("'{}' is not an integer.  Please try again.".format(response))
            continue
            
    raise Cancel("Retries exceeded")
    
    
def yes_no_cancel(string=""):
    retries = 0
    while retries < 5:
        retries += 1
        response = input_with_cancel(string)
        response = response.upper()
        if response == "" or response == "Y":
            return True
        elif response == "N":
            return False
        else:
            print("Unrecognised response '{}'. Please try again.".format(response))
    
    raise Cancel("Retries exceeded.")
    