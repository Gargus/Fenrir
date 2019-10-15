class BankException(Exception):
    def __init__(self):
        self.error_string = 'User do not have enough currency'
    def __str__(self):
        return self.error_string
class PickException(Exception):
    def __init__(self):
        self.error_string = 'The selected pick does not exist'
    def __str__(self):
        return self.error_string