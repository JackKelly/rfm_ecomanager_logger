#!/usr/bin/python
from __future__ import print_function, division
import argparse, os, sys, datetime, pytz, ConfigParser, shutil
import logging.handlers
log = logging.getLogger("merge_datasets")

DATE_FMT = '%d/%m/%Y %H:%M:%S %Z'
MIN_VOLTAGE = 200 # minimum acceptable voltage for mains voltage recorded using snd_card_power_meter
AGGREGATE_LABELS = ['agg','aggregate','mains','whole-house', 'wholehouse', 'whole house']
THRESHOLD_FOR_IAMS = 4090 # watts.  4096 (2^{12}) is a common anomalous number 
THRESHOLD_FOR_AGGREGATE = 20000 # watts

def setup_argparser():
    # Process command line _args
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     usage=
"""
DESCRIPTION
===========

rfm_ecomanager_logger creates a new, numerically labelled data directory
every time it is run.  merge_datasets.py merges these datasets into
a single dataset directory and also removes insanely large values and the
phase difference column from snd_card_power_meter data (because that column
is garbage!)

REQUIREMENTS
============

Create a labels.dat file for your target data directory.  The labels are
case sensitive.  This file can include multiple synonyms on each line,
separated by a forward slash "/".  For example:
   
     1 aggregate / agg / mains
     2 toaster
     3 tv / television
     
Specifying synonyms is useful if the input datasets use different labels
for the same appliance.  The first name in a list of synonyms will be used
in the output labels.dat file.

USAGE
=====
   
Run merge_datasets as follows:

  ./merge_datasets.py <BASE_DATA_DIR> 
    --template-labels-file <TEMPLATE LABELS.DAT>
    --output-dir <OUTPUT_DIRECTORY>
    [--dry-run]
    [--scpm-data-dir] <SCPM_DATA_DIRECTORY>

<BASE_DATA_DIR> 
  Will be searched recursively for input data directories containing valid
  data.  The following logic is performed on each directory:
  - Does the directory contain a labels.dat file? 
      If not then:
          the directory is assumed to not be a data directory and will be
          searched recursively for more data directories.
      If it does then proceed with further checks:
  - Does the directory contain at least one channel_??.dat file?  
    If not then ignore it.
  - If a channel is listed in the labels.dat file but there
    is no corresponding channel_??.dat file then that channel is ignored.

<OUTPUT_DIRECTORY>
  Will be populated with:
  - all merged channel_??.dat files
  - a new labels.dat file based on the target labels.dat file.  If any
    input data directory contains valid channels not listed in the 
    target labels.dat file then those channels will be appended to the end
    of the target labels.
  - a merge_datasets.log file
  
  All channel_*.dat files and merge_datasets.log in <OUTPUT_DIRECTORY> will be
  deleted when merge_datasets.py starts, to make way for the new files.
  
--dry-run
  Can optionally be specified to check that the proposed order
  of the input data directories is correct before actually merging the files.
  Specifying --dry-run will also disable deletion of *.dat files 
  in <OUTPUT_DIRECTORY>.
  
--scpm-data-dir
  Optionally provide a base directory for data recorded using the
  Sound Card Power Meter project.  These .dat files will be merged into one
  large mains.dat file.
    
"""                                     )
 
    parser.add_argument('base_data_dir')

    parser.add_argument('--template-labels-filename', type=str,
                        help='The labels file to attempt to conform all input'
                        ' datasets to.', required=True)
    
    parser.add_argument('--output-dir', type=str, required=True)
    
    parser.add_argument('--scpm-data-dir', type=str)
    
    parser.add_argument('--dry-run', action='store_true')
        
    args = parser.parse_args()

    args.base_data_dir = os.path.expanduser(args.base_data_dir)
    args.template_labels_filename = os.path.expanduser(args.template_labels_filename)
    args.output_dir = os.path.expanduser(args.output_dir)
    if args.scpm_data_dir:
        args.scpm_data_dir = os.path.expanduser(args.scpm_data_dir)

    return args


def init_logger(log_filename):
    log.setLevel(logging.DEBUG)

    # date formatting
    datefmt = "%y-%m-%d %H:%M:%S %Z"

    # create console handler (ch) for stdout
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter('%(asctime)s %(levelname)s '
                        '%(message)s', datefmt=datefmt)
    ch.setFormatter(ch_formatter)
    log.addHandler(ch)

    # create file handler (fh) for babysitter.log
    fh = logging.FileHandler(log_filename, mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(ch_formatter)    
    log.addHandler(fh)


class Dataset(object):
    def __init__(self, data_dir=None):
        self.data_dir = data_dir        
        if self.data_dir is not None:
            self.load_metadata()            
            self.get_timestamp_range()
            self.start_datetime = datetime.datetime.fromtimestamp(self.first_timestamp,
                                                                  self.tz)
            self.last_datetime = datetime.datetime.fromtimestamp(self.last_timestamp,
                                                                  self.tz)
            self.timedelta = self.last_datetime - self.start_datetime            
            self.labels = load_labels_file(os.path.join(self.data_dir,
                                                        'labels.dat'))

    def load_metadata(self):
        self.metadata_parser = load_metadata(self.data_dir)
        tz_string = get_tz_string_from_metadata(self.metadata_parser)
        if not tz_string:
            tz_string = get_local_machine_tz_string()
            log.debug("No timezone info for {} so using local machine's tz = {}"
                      .format(self.data_dir, tz_string))            
        self.tz = pytz.timezone(tz_string)

    def __str__(self):
        s = '\n'
        s += '     ' + self.data_dir + '\n'
        
        s += '       start = ' + self.start_datetime.strftime(DATE_FMT) + '\n'
        s += '         end = ' + self.last_datetime.strftime(DATE_FMT) + '\n'
        s += '    duration = {}'.format(self.timedelta) + '\n'
        s += '      labels = {}'.format(self.labels) + '\n'
        s += '\n'
        return s

    def get_timestamp_range(self):
        """
        Opens all channel_?.dat files in data_dir and finds the first and last
        timestamps across all dat files. 

        Returns:
            first_timestamp (float), last_timestamp (float)
        """    
        first_timestamp = None
        last_timestamp = None
        
        MIN_FILESIZE = 13 # a single line of data is at least 13 bytes
        
        def get_timestamp_from_line(line):
            return float(line.split(' ')[0])
        
        for data_filename in self.get_data_filenames():
            full_filename = os.path.join(self.data_dir, data_filename)
            file_size = os.path.getsize(full_filename)
            if file_size < MIN_FILESIZE:
                log.warn("file does not contain enough data: " + full_filename)
                continue
            with open(full_filename) as fh:
                first_line = fh.readline()
                file_first_timestamp = get_timestamp_from_line(first_line)
                
                if file_size > MIN_FILESIZE*2:
                    # If the file is sufficiently large then
                    # seek to the end of the file minus two lines
                    fh.seek(-MIN_FILESIZE*2, 2)
                    
                last_lines = fh.readlines()
                if last_lines: 
                    last_line = last_lines[-1]
                else:
                    last_line = first_line

                try:
                    file_last_timestamp = get_timestamp_from_line(last_line)
                except:
                    print("Failed to read last line of file '{:s}'. Last line='{:s}'"
                          .format(full_filename, last_line), file=sys.stderr)
                    raise
            
            if first_timestamp is None or file_first_timestamp < first_timestamp:
                first_timestamp = file_first_timestamp
    
            if last_timestamp is None or file_last_timestamp > last_timestamp:
                last_timestamp = file_last_timestamp
    
        self.first_timestamp = first_timestamp
        self.last_timestamp = last_timestamp
        return first_timestamp, last_timestamp

    def get_data_filenames(self):
        """            
        Returns:
            list of strings representing .dat filenames, including .dat suffix;
            not including the directory.  Only returns files of the form
            channel_??.dat
        """
        all_filenames = os.walk(self.data_dir).next()[2]
        data_filenames = [f for f in all_filenames
                          if f.startswith('channel_') and f.endswith('.dat')]
        return data_filenames


def load_labels_file(labels_filename):
    """
    Args:
        labels_filename (str): including full path
        
    Returns:
        dict mapping channel number to label
    """
    with open(labels_filename) as labels_file:
        lines = labels_file.readlines()
    
    labels = {}
    for line in lines:
        split_line = line.partition(' ')
        try:
            labels[int(split_line[0])] = split_line[2].strip()
        except ValueError:
            log.warn("unprocessed line from labels.dat: '" + line + "'")

    log.debug("Loaded {} lines from {}".format(len(labels), labels_filename))
        
    return labels
    

def split_label_synonyms(labels):
    """
    Args:
        labels (dict): mapping chan num (int) to label (string)
    Returns:
        dict mapping channel num to a list of strings. e.g.:
        {1: ['aggregate', 'agg']}
    """
    for key, item in labels.iteritems():
        synonyms = [label.strip() for label in item.split('/')]
        labels[key] = synonyms
        
    return labels


class TemplateLabels(object):
    """
    Attributes:
        label_to_chan (dict): maps a single string to a channel number (int).
                              Synonyms map to the same chan number.
                              
        synonym_to_primary (dict): maps secondary synonyms to primary label
                              (primary label = the one used in the target
                               label.dat file)
    """
    
    def __init__(self, labels_filename):
        template_labels = load_labels_file(labels_filename)
        template_labels = split_label_synonyms(template_labels)

        # Create a mapping from chan number to label
        self.label_to_chan = {}
        self.synonym_to_primary = {}
        for chan, labels in template_labels.iteritems():
            for label in labels:
                self.label_to_chan[label] = chan
            for label in labels[1:]:
                self.synonym_to_primary[label] = labels[0]

    def assimilate_and_get_map(self, dataset):
        """
        If data_dir/labels.dat contains any labels not in self.labels
        then add those labels to self.labels.
        Return a mapping from source labels to template labels.
        
        Args:
            dataset (Dataset)
            
        Returns:
            dict mapping from source labels index to template labels index.
            e.g.
                {1: 1,  2: 3,  3: 2}
                maps source labels 1, 2 and 3 to template labels 1, 3 and 2
        """      
        source_to_template = {} # what we return
        
        for chan, label in dataset.labels.iteritems():
            # filter out any labels for data files which don't exist
            chan_filename = os.path.join(dataset.data_dir, 
                                         "channel_{:d}.dat".format(chan))
            if not os.path.exists(chan_filename):
                log.debug("does not exist: " + chan_filename)
                continue
        
            # Figure out if any items in source_labels are not in self.labels
            if not self.label_to_chan.has_key(label):
                self.label_to_chan[label] = max(self.label_to_chan.values())+1
                log.info("added {} as {}".format(label,
                                                 self.label_to_chan[label]))
                
            source_to_template[chan] = self.label_to_chan[label]
            
        return source_to_template
    
    def write_to_disk(self, data_dir):
        """
        Write a labels.dat file to data_dir.
        """
        # Assemble a dict mapping chan number to label
        chan_to_label = {}
        for label, chan in self.label_to_chan.iteritems():
            chan_to_label[chan] = self.synonym_to_primary.get(label, label)
        
        with open(os.path.join(data_dir, 'labels.dat'), 'w') as fh:
            for chan in sorted(chan_to_label.iterkeys()):
                fh.write('{} {}\n'.format(chan, chan_to_label[chan]))


def get_channel_from_filename(data_filename):
    """
    Args:
        data_filename (str)
        
    Returns:
        int
    """
    channel_str = data_filename.lstrip('channel_').rstrip('.dat')
    return int(channel_str)


def remove_values_above(threshold, line):
    """
    Args:
        threshold (float)
        line (str)
    """
    parts = line.split(' ')
    watts = float(parts[1])
    
    if watts > threshold:
        return None
    else:
        return line


def process_high_freq_line(data):
    data = data.split(' ')
    data[-1] = data[-1].strip()

    # Remove phase diff column (because it's garbage!)
    data = data[:4]

    # Ignore entire line if voltage is insanely low
    try:
        voltage = float(data[3])
    except IndexError:
        return None

    if voltage < MIN_VOLTAGE:
        return None

    data = ' '.join(data) + '\n'
    return data


def append_files(input_filename, output_filename, 
                 line_processing_func=lambda x: x):
    """
    Appends input_filename onto the end of output_filename.
    
    Args:
        input_filename, output_filename (str): full paths to files
        line_processing_func (function): Optional. A suitable function must 
            take a single line as input and return a processed line or None.
    """
    input_file = open(input_filename, 'r')    
    output_file = open(output_filename, 'a')
    while True:
        data = input_file.readline()
        if data and data.strip():
            try:
                data = line_processing_func(data)
            except Exception as e:
                log.warn("Problem processing line in file '{}' while"
                         " concatenating with '{}'."
                         " Troublesome input line = '{}'. Error was: '{}'"
                         .format(input_filename, output_filename, data, e))
            else:
                if data is not None:
                    output_file.write(data)
        else:
            break
    input_file.close()
    output_file.close()


def get_all_data_dirs(base_data_dir):
    """Returns a list of all full directories which contains a labels.dat
    file, starting from base_data_dir and recursing downwards through the
    directory tree.
    """

    # Recursive.  If base_data_dir has a labels.dat file then
    # it's a data dir.  Else recurse through the dir structure.
    labels_filename = os.path.join(base_data_dir, 'labels.dat')
    processed_subdirs = []
    if os.path.exists(labels_filename):
        # make sure there is at least one channel_* file
        channel_files = [f for f in os.listdir(base_data_dir) 
                         if f.startswith('channel_') and
                         os.path.getsize(os.path.join(base_data_dir, f)) > 12]
        if channel_files:
            processed_subdirs.append(base_data_dir)
        else:
            log.warn(base_data_dir + " contains no valid channel_??.dat files")
    else:
        # Recurse through any directories which don't have a labels.dat

        # Get just the names of the directories within base_data_dir
        # Taken from http://stackoverflow.com/a/142535/732596
        subdirs = os.walk(base_data_dir).next()[1]
        for subdir in subdirs:
            full_subdir = os.path.join(base_data_dir, subdir)                
            processed_subdirs.extend(get_all_data_dirs(full_subdir))

    return processed_subdirs


def check_not_overlapping(datasets):
    if not datasets:
        return
    
    last_timestamp = datasets[0].last_timestamp
    for dataset in datasets[1:]:
        if last_timestamp > dataset.first_timestamp:
            sys.exit("ERROR: {} starts before the previous dataset finishes!"
                     .format(dataset.data_dir))
        last_timestamp = dataset.last_timestamp


def load_metadata(data_dir):
    metadata_parser = ConfigParser.RawConfigParser()
    metadata_parser.read(os.path.join(data_dir, 'metadata.dat'))
    return metadata_parser


def get_local_machine_tz_string():
    TZFILE_NAME = '/etc/timezone'
    f = open(TZFILE_NAME)
    local_tz_string = f.readline()
    f.close()
    return local_tz_string.strip()


def get_tz_string_from_metadata(metadata_parser):
    try:
        tz_string = metadata_parser.get('datetime', 'timezone')
    except ConfigParser.Error:
        tz_string = ""
    return tz_string


def merge_metadata(dst, src):
    """
    Goes through every section and every option in src. If any option is 
    not present in dst or different in dst then create or overwrite option
    in dst with value from src.
    
    Args:
        dst, src (ConfigParser.RawConfigParser)
    Return:
        dst (ConfigParser.RawConfigParser)
    """
    for section in src.sections():
        for option in src.options(section):
            src_value = src.get(section, option)
            try:
                dst_value = dst.get(section, option)
            except ConfigParser.NoSectionError:
                dst.add_section(section)
                dst.set(section, option, src_value)
            except ConfigParser.NoOptionError:
                dst.set(section, option, src_value)
            else:
                if src_value != dst_value:
                    log.warn("section={}, option={}, src value={}, dst value={}"
                             .format(section, option, src_value, dst_value))
                    dst.set(section, option, src_value) 
    return dst


def main():
    args = setup_argparser()

    if not os.path.exists(args.output_dir) and not args.dry_run:
        os.makedirs(args.output_dir)
    
    init_logger(os.path.join(args.output_dir, 'merge_datasets.log'))
    
    template_labels = TemplateLabels(args.template_labels_filename)
    
    data_directories = get_all_data_dirs(args.base_data_dir)
    
    # First find the correct ordering for the datasets:
    datasets = []
    for data_dir in data_directories:
        datasets.append(Dataset(data_dir))
    datasets.sort(key=lambda dataset: dataset.first_timestamp)
        
    log.info("Proposed order :")
    total_uptime = datetime.timedelta()
    for dataset in datasets:
        log.info(str(dataset))
        total_uptime += dataset.timedelta
    
    check_not_overlapping(datasets)
    log.info("Good: datasets are not overlapping")
    
    timespan = datasets[-1].last_datetime - datasets[0].start_datetime
    log.info("For whole dataset: \n"
             "  start time = " + datasets[0].start_datetime.strftime(DATE_FMT) + "\n"
             "    end time = " + datasets[-1].last_datetime.strftime(DATE_FMT) + "\n"
             "    timespan = {}\n".format(timespan) + 
             "      uptime = {}\n".format(total_uptime) + 
             "    % uptime = {:.1%}\n".format(total_uptime.total_seconds() / 
                                        timespan.total_seconds()))
    
    if not args.dry_run:
        # Remove all the old files in the output dir        
        files_to_delete = [f for f in os.listdir(args.output_dir) 
                           if f.startswith('channel_') and f.endswith('.dat')] 
        files_to_delete.append('labels.dat')
        files_to_delete.append('mains.dat')
        log.info("Deleting {} old files in {}"
                 .format(len(files_to_delete), args.output_dir))    
        for filename in files_to_delete:
            try:
                os.remove(os.path.join(args.output_dir, filename))
            except Exception as e:
                log.warn(str(e))

        # Copy README.txt and .dat files in base_data_dir, if they exist
        files_to_copy = os.listdir(args.base_data_dir)
        files_to_copy = [file for file in files_to_copy 
                         if file.endswith('.txt') or file.endswith('.dat')]
        for file in files_to_copy:
            fname = os.path.join(args.base_data_dir, file)
            if os.path.exists(fname):
                log.info("Copying " + fname)
                shutil.copy2(fname, args.output_dir)
            else:
                log.info(fname + " does not exist so will not copy it!")
    
    output_metadata_parser = ConfigParser.RawConfigParser()
    
    # Now merge the datasets
    if not args.dry_run:
        log.info("Merging files...")

    for dataset in datasets:
        labels_map = template_labels.assimilate_and_get_map(dataset)
        
        for data_filename in dataset.get_data_filenames():
            input_channel = get_channel_from_filename(data_filename)
            input_filename = os.path.join(dataset.data_dir, data_filename)
            output_channel = labels_map[input_channel]
            output_filename = os.path.join(args.output_dir,
                                           'channel_{:d}.dat'
                                           .format(output_channel))
            log.debug("appending " + input_filename + 
                     " to end of " + output_filename)
            if not args.dry_run:
                label = dataset.labels[input_channel]
                if label in AGGREGATE_LABELS:
                    threshold = THRESHOLD_FOR_AGGREGATE
                else:
                    threshold = THRESHOLD_FOR_IAMS
                line_proc_f = lambda line: remove_values_above(threshold, line)
                append_files(input_filename, output_filename, 
                             line_processing_func=line_proc_f)
                
        # Handle metadata
        output_metadata_parser = merge_metadata(output_metadata_parser,
                                                dataset.metadata_parser)

    if not args.dry_run:
        log.info("Writing new labels file to disk")
        template_labels.write_to_disk(args.output_dir)
        
        # Set default timezone in metadata if necessary
        if not output_metadata_parser.has_section('datetime'):
            output_metadata_parser.add_section('datetime')
        if not output_metadata_parser.has_option('datetime', 'timezone'):
            log.info("Setting default timezone in output metadata.dat")
            output_metadata_parser.set('datetime', 'timezone', 
                                       get_local_machine_tz_string())

        # Write metadata to file
        # with open(os.path.join(args.output_dir, 'metadata.dat'), 'wb') as f:
        #     output_metadata_parser.write(f)
            
    # Process Sound Card Power Meter data if scpm-data-dir is set
    if args.scpm_data_dir:
        args.scpm_data_dir = os.path.realpath(args.scpm_data_dir)
        log.info("Processing SCPM data dir = " + args.scpm_data_dir)
        mains_files = [mf for mf in os.listdir(args.scpm_data_dir)
                       if mf.startswith('mains-') and mf.endswith('.dat')]
        mains_files.sort()
        output_filename = os.path.join(args.output_dir, 'mains.dat')
        log.info("Proposed order for SCPM data: {}".format(mains_files))
        if not args.dry_run:
            for mains_file in mains_files:
                input_filename = os.path.join(args.scpm_data_dir, mains_file)
                append_files(input_filename, output_filename,
                             line_processing_func=process_high_freq_line)

if __name__=="__main__":
    main()
