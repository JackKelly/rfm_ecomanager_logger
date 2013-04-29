import unittest, os, inspect, ConfigParser, sys

# Hack to allow us to import ../rfm_ecomanager_logger
# Take from http://stackoverflow.com/a/6098238/732596
FILE_PATH = os.path.dirname(inspect.getfile(inspect.currentframe()))
RFM_ECOMANAGER_LOGGER_SUBFOLDER = os.path.realpath(os.path.join(FILE_PATH,
                                                                '..',
                                                                'rfm_ecomanager_logger'))
if RFM_ECOMANAGER_LOGGER_SUBFOLDER not in sys.path:
    sys.path.insert(0, RFM_ECOMANAGER_LOGGER_SUBFOLDER)
import rfm_ecomanager_logger as rfm

TEMP_OUTPUT_PATH = os.path.join(FILE_PATH, 'temp_output')

class Args(object):
    def __init__(self):
        self.data_directory = ""
        if not os.path.exists(TEMP_OUTPUT_PATH):
            os.mkdir(TEMP_OUTPUT_PATH)

class TestManager(unittest.TestCase):
    def setUp(self):
        self.m = rfm.Manager(None, Args())
        self.m.args.data_directory = TEMP_OUTPUT_PATH
        
    def test_create_metadata_file(self):
        metadata_filename = self.m._create_metadata_file()
        metadata_parser = ConfigParser.RawConfigParser()
        metadata_parser.read(metadata_filename)
        tz = metadata_parser.get('datetime', 'timezone')
        self.assertEqual(tz, 'Europe/London')
        os.remove(metadata_filename)

if __name__ == "__main__":
    unittest.main()
