import unittest, os, sys, inspect, shutil

# Hack to allow us to import ../scripts/merge_datasets.py
# Take from http://stackoverflow.com/a/6098238/732596
FILE_PATH = os.path.dirname(inspect.getfile(inspect.currentframe()))
SCRIPTS_SUBFOLDER = os.path.realpath(os.path.join(FILE_PATH, '..', 'scripts'))
if SCRIPTS_SUBFOLDER not in sys.path:
    sys.path.insert(0, SCRIPTS_SUBFOLDER)
import merge_datasets as md

BASE_TEST_DATA_DIR = os.path.join(FILE_PATH, 'test_data')
TARGET_LABELS_FILENAME = os.path.join(FILE_PATH, 'target_labels', 'labels.dat')

class TestMergeDatasets(unittest.TestCase):
    
    def setUp(self):
        pass
        
    def test_get_channel_from_filename(self):
        self.assertEqual(md.get_channel_from_filename('channel_1.dat'), 1)
        self.assertEqual(md.get_channel_from_filename('channel_01.dat'), 1)
        self.assertEqual(md.get_channel_from_filename('channel_50.dat'), 50)
        self.assertEqual(md.get_channel_from_filename('channel_0.dat'), 0)
        
    def test_load_labels_file(self):
        labels_filename = os.path.join(BASE_TEST_DATA_DIR, '001', 'labels.dat')
        l = md.load_labels_file(labels_filename)
        self.assertEqual(l[1], 'aggregate')
        self.assertEqual(l[17], 'amp_livingroom')
        
    def test_labels_synonyms(self):
        labels = {1: 'aggregate / agg', 2: 'usb / usb&gigE',
                  4: 'light', 5: 'this and that and those'}
        labels = md.split_label_synonyms(labels)
        self.assertEqual(labels[1], ['aggregate', 'agg'])
        self.assertEqual(labels[2], ['usb', 'usb&gigE'])
        self.assertEqual(labels[4], ['light'])
        self.assertEqual(labels[5], ['this and that and those'])
        
    def test_template_labels_init(self):
        tl = md.TemplateLabels(TARGET_LABELS_FILENAME)
        self.assertEqual(tl.label_to_chan['aggregate'], 1)
        self.assertEqual(tl.label_to_chan['agg'], 1)
        self.assertEqual(tl.label_to_chan['laptop'], 4)
        self.assertEqual(tl.label_to_chan['tv'], 7)
        self.assertEqual(tl.label_to_chan['television'], 7)
        self.assertEqual(tl.label_to_chan['coffee'], 17)
        
        self.assertEqual(tl.synonym_to_primary['agg'], 'aggregate')
        
        return tl
    
    def test_write_to_disk(self):
        tl = self.test_template_labels_assimilate_and_get_map()
        tl.write_to_disk(BASE_TEST_DATA_DIR)
        labels_filename = os.path.join(BASE_TEST_DATA_DIR, 'labels.dat')
        labels_dict = md.load_labels_file(labels_filename)
        os.remove(labels_filename)        
        correct_dict = {1: 'aggregate', 2: 'boiler', 3: 'solar', 4: 'laptop',
                        5: 'washing_machine', 6: 'dishwasher', 7: 'tv', 
                        8: 'kitchen_lights', 9: 'htpc', 10: 'kettle', 
                        11: 'toaster', 12: 'fridge', 13: 'microwave', 
                        14: 'lcd_office', 15: 'breadmaker', 16: 'hifi_office', 
                        17: 'coffee', 18: 'amp_livingroom', 19: 'adsl_router'}
        self.assertEqual(labels_dict, correct_dict)
        
    def test_template_labels_assimilate_and_get_map(self):
        labels_filename = TARGET_LABELS_FILENAME
        tl = md.TemplateLabels(labels_filename)
        
        source_data_dir = os.path.join(BASE_TEST_DATA_DIR, '001')
        
        stt = tl.assimilate_and_get_map(md.Dataset(source_data_dir))
        
        self.assertEqual(stt[1], 1) 
        self.assertEqual(stt[16], 15) # breadmaker
        self.assertEqual(stt[18], 19) # adsl_router
        
        return tl

    def test_get_all_data_dirs(self):
        data_dirs = md.get_all_data_dirs(BASE_TEST_DATA_DIR)
        
        correct_data_dirs = ['001', '002', 
                             'dir_with_more_data_dirs/003', 
                             'dir_with_more_data_dirs/003']
        
        correct_data_dirs = [os.path.join(BASE_TEST_DATA_DIR, d) 
                             for d in correct_data_dirs]
        
        self.assertEqual(data_dirs.sort(), correct_data_dirs.sort())
        

    def test_append_data(self):
        DIR = os.path.join(BASE_TEST_DATA_DIR, 'append_data_test_fodder')
        shutil.copyfile(os.path.join(DIR, 'apendee.dat'),
                        os.path.join(DIR, 'apendee_backup.dat') )

        md.append_files(os.path.join(DIR, 'to_append.dat'),
                       os.path.join(DIR, 'apendee.dat'))
        
        f = open(os.path.join(DIR, 'apendee.dat'), 'r')
        lines = f.readlines()
        f.close()
        
        self.assertEqual(lines, ['1 1.0\n', '2 2.0\n', '3 3.0\n', '4 4.0\n'])

        shutil.move(os.path.join(DIR, 'apendee_backup.dat'),
                    os.path.join(DIR, 'apendee.dat'))
        
    def test_get_timestamp_range(self):
        DIR = os.path.join(BASE_TEST_DATA_DIR, '001')
        dataset = md.Dataset(DIR)
        first_timestamp, last_timestamp = dataset.get_timestamp_range()
        self.assertEqual(first_timestamp, 1360396444.0)
        self.assertEqual(last_timestamp, 1360400145.0)            
        
    def test_check_not_overlapping(self):
        ds1 = md.Dataset()
        ds1.first_timestamp = 1
        ds1.last_timestamp = 100
        ds1.data_dir = '1'
        
        ds2 = md.Dataset()
        ds2.first_timestamp = 101
        ds2.last_timestamp = 200
        ds2.data_dir = '2'
        
        ds3 = md.Dataset()
        ds3.first_timestamp = 200
        ds3.last_timestamp = 300
        ds3.data_dir = '3'
        
        datasets = [ds1, ds2, ds3]
        md.check_not_overlapping(datasets)

if __name__ == "__main__":
    unittest.main()
