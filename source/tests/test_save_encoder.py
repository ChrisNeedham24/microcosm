import unittest

from source.foundation.models import Effect
from source.saving.save_encoder import SaveEncoder, ObjectConverter


class SaveEncoderTest(unittest.TestCase):
    """
    The test class for save_encoder.py.
    """

    def test_save_encoder(self):
        test_effect = Effect(wealth=1, harvest=2, zeal=3, fortune=4, strength=5, satisfaction=6)
        test_effect_as_dict = {
            "wealth": test_effect.wealth,
            "harvest": test_effect.harvest,
            "zeal": test_effect.zeal,
            "fortune": test_effect.fortune,
            "strength": test_effect.strength,
            "satisfaction": test_effect.satisfaction
        }
        test_set = set()
        test_set.add("a")
        test_set.add("b")
        test_converter = ObjectConverter(test_effect_as_dict)

        save_encoder = SaveEncoder()

        # The data class should be transformed into a dictionary, the set into a list, and the ObjectConverter into a
        # dictionary as well.
        self.assertDictEqual(test_effect_as_dict, save_encoder.default(test_effect))
        self.assertTrue(isinstance(save_encoder.default(test_set), list))
        self.assertEqual(test_effect_as_dict, save_encoder.default(test_converter))


if __name__ == '__main__':
    unittest.main()
