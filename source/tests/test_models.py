import unittest
from datetime import datetime

from source.foundation.models import SaveDetails


class ModelsTest(unittest.TestCase):
    """
    The test class for models.py.
    """

    def test_save_details_formatted_name(self):
        """
        Ensure that formatted names for SaveDetails objects are correctly generated.
        """
        save: SaveDetails = SaveDetails(datetime(1970, 1, 2, 3, 4, 5), auto=False)
        autosave: SaveDetails = SaveDetails(datetime(1980, 2, 3, 4, 5, 6), auto=True)
        self.assertEqual("1970-01-02 03:04:05", save.get_formatted_name())
        self.assertEqual("1980-02-03 04:05:06 (auto)", autosave.get_formatted_name())


if __name__ == '__main__':
    unittest.main()
