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
        
    def test_template_labels_assimilate_and_get_map(self):
        labels_filename = TARGET_LABELS_FILENAME
        tl = md.TemplateLabels(labels_filename)
        
        source_data_dir = os.path.join(BASE_TEST_DATA_DIR, '001')
        
        stt = tl.assimilate_and_get_map(source_data_dir)
        
        self.assertEqual(stt[1], 1) 
        self.assertEqual(stt[16], 15) # breadmaker
        self.assertEqual(stt[18], 19) # adsl_router

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
                    

if __name__ == "__main__":
    unittest.main()
