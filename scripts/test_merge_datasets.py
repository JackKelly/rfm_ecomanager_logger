import merge_datasets as md
import unittest

class TestMergeDatasets(unittest.TestCase):
    
    def setUp(self):
        pass
        
    def test_get_channel_from_filename(self):
        self.assertEqual(md.get_channel_from_filename('channel_1.dat'), 1)
        self.assertEqual(md.get_channel_from_filename('channel_01.dat'), 1)
        self.assertEqual(md.get_channel_from_filename('channel_50.dat'), 50)
        self.assertEqual(md.get_channel_from_filename('channel_0.dat'), 0)
        

if __name__ == "__main__":
    unittest.main()
