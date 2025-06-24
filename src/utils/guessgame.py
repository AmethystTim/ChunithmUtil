class GuessGame():
    def __init__(self):
        self.games = {}
        self.timelimit = 30
        
    def add_group(self, group: str):
        self.games[group] = -1
    
    def remove_group(self, group: str):
        self.games.pop(group, None)
    
    def get_group_index(self, group: str) -> int:
        if group not in self.games.keys():
            return -1
        return self.games[group]
    
    def set_song_index(self, group: str, index: int):
        if group not in self.games.keys():
            return
        self.games[group] = index
    
    def check_is_exist(self, group: str) -> bool:
        return group in self.games.keys()
    
    def check_is_correct(self, group: str, index: int) -> bool:
        if not self.check_is_exist(group):
            return False
        return str(self.games[group]) == str(index)