import json
import os


SETTINGS_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'cache', 'others', 'guess_settings.json'
)


class GuessGame():
    def __init__(self):
        self.games = {}
        self.timelimit = 30
        self.const_ranges = self._load_const_ranges()
        
    def _load_const_ranges(self) -> dict:
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

        ranges = {}
        if not isinstance(data, dict):
            return ranges
        for group, values in data.items():
            if not isinstance(values, dict):
                continue
            minimum = values.get("min")
            maximum = values.get("max")
            if minimum is not None and not isinstance(minimum, (int, float)):
                continue
            if maximum is not None and not isinstance(maximum, (int, float)):
                continue
            if minimum is not None and maximum is not None and minimum > maximum:
                continue
            ranges[str(group)] = {
                "min": float(minimum) if minimum is not None else None,
                "max": float(maximum) if maximum is not None else None,
            }
        return ranges

    def _save_const_ranges(self) -> None:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        temp_path = f"{SETTINGS_PATH}.tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(self.const_ranges, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, SETTINGS_PATH)

    def get_const_range(self, group: str) -> tuple[float | None, float | None]:
        values = self.const_ranges.get(group, {})
        return values.get("min"), values.get("max")

    def set_const_range(
        self, group: str, minimum: float, maximum: float | None = None
    ) -> None:
        self.const_ranges[group] = {"min": minimum, "max": maximum}
        self._save_const_ranges()

    def clear_const_range(self, group: str) -> bool:
        if group not in self.const_ranges:
            return False
        self.const_ranges.pop(group)
        self._save_const_ranges()
        return True

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