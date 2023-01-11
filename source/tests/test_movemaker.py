import unittest


class MovemakerTest(unittest.TestCase):
    """
    The test class for movemaker.py.
    """

    """
    Set blessing cases to test

    No available blessings
    Player requires wealth
    Player requires harvest
    Player requires zeal
    Player requires fortune
    Aggressive AI chooses unit
    Aggressive AI no units, takes ideal
    Defensive AI chooses strength
    Defensive AI no strength, takes ideal
    """

    """
    Search for relics or move cases to test

    Search succeeds, to left of relic
    Search succeeds, to right of relic
    Search fails because relic surrounded by player unit, AI unit, and settlement
    No relics found - random movement
    """


if __name__ == '__main__':
    unittest.main()
