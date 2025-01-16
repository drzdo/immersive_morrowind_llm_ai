class Distance:
    @staticmethod
    def from_ingame_to_meters(ingame: float):
        # in game -> yard -> meter
        return ingame / 64.0 * 0.9144

    @staticmethod
    def from_meters_to_ingame(meters: float):
        # meter -> yard -> in game
        return meters / 0.9144 * 64.0
