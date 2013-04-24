#!/usr/bin/python
from __future__ import print_function, division
import argparse, os

def setup_argparser():
    # Process command line _args
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=
"""
DESCRIPTION
===========

rfm_ecomanager_logger creates a new, numerically labelled data directory
every time it is run.  merge_datasets.py aims to merge these datasets into
a single dataset directory.

USAGE
=====

1. Create a labels.dat file for your target data directory.  This
   file can include multiple synonyms on each line, separated by a /
   
   For example:
     1 aggregate / agg / mains
     2 toaster
     3 tv / television
     
   Specifying synonyms is useful if the input datasets use different labels
   for the same appliance.
"""                                     )

    parser.add_argument('base-data-dir')

    parser.add_argument('--template-labels-filename', type=str,
                        help='The labels file to attempt to conform all input'
                        ' datasets to.', required=True)
    
    parser.add_argument('--output-dir', type=str, required=True)
        
    return parser.parse_args()


class Dataset(object):
    def __init__(self, data_dir):
        first_timestamp, last_timestamp = get_timestamp_range(data_dir)
        self.first_timestamp = first_timestamp
        self.last_timestamp = last_timestamp
        self.data_dir = data_dir


def get_timestamp_range(data_dir):
    """
    Opens all channel_?.dat files in data_dir and finds the first and last
    timestamps across all dat files. 
    
    Args:
        data_dir (str)
        
    Returns:
        first_timestamp (float), last_timestamp (float)
    """
    all_filenames = os.walk(data_dir).next()[2]
    data_filenames = [f for f in all_filenames
                      if f.startswith('channel_') and f.endswith('.dat')]
    
    first_timestamp = None
    last_timestamp = None
    
    def get_timestamp_from_line(line):
        return float(line.split(' ')[0])
    
    for data_filename in data_filenames:
        with open(os.path.join(data_dir, data_filename)) as fh:
            first_line = next(fh).decode()
            file_first_timestamp = get_timestamp_from_line(first_line)
            fh.seek(-1024, 2)
            last_line = fh.readlines()[-1].decode()
            file_last_timestamp = get_timestamp_from_line(last_line)
        
        if first_timestamp is None or file_first_timestamp < first_timestamp:
            first_timestamp = file_first_timestamp

        if last_timestamp is None or file_last_timestamp > last_timestamp:
            last_timestamp = file_last_timestamp

    return first_timestamp, last_timestamp


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
        line = line.partition(' ')
        labels[int(line[0])] = line[2].strip()

    print("Loaded {} lines from {}".format(len(labels), labels_filename))
        
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
    """
    
    def __init__(self, labels_filename):
        template_labels = load_labels_file(labels_filename)
        template_labels = split_label_synonyms(template_labels)

        # Create a mapping from chan number to label
        self.label_to_chan = {}
        for chan, labels in template_labels.iteritems():
            for label in labels:
                self.label_to_chan[label] = chan

    def assimilate_and_get_map(self, data_dir):
        """
        If data_dir/labels.dat contains any labels not in self.labels
        then add those labels to self.labels and return a mapping
        from source labels to template labels.
        
        Args:
            data_dir (str)
            
        Returns:
            dict mapping from source labels index to template labels index.
            e.g.
                {1: 1,  2: 3,  3: 2}
                maps source labels 1, 2 and 3 to template labels 1, 3 and 2
        """
        labels_filename = os.path.join(data_dir, 'labels.dat')
        source_labels = load_labels_file(labels_filename)
        
        source_to_template = {} # what we return
        
        for chan, label in source_labels.iteritems():
            # filter out any labels for data files which don't exist
            chan_filename = os.path.join(data_dir, 
                                         "channel_{:d}.dat".format(chan))
            if not os.path.exists(chan_filename):
                continue
        
            # Figure out if any items in source_labels are not in self.labels
            if not self.label_to_chan.has_key(label):
                self.label_to_chan[label] = max(self.label_to_chan.values())+1
                print("added", label, "as", self.label_to_chan[label])
                
            source_to_template[chan] = self.label_to_chan[label]
            
        return source_to_template

def get_data_filenames(data_dir):
    """
    Args:
        data_dir (str)
        
    Returns:
        list of strings representing .dat filenames, including .dat suffix;
        not including the directory.
    """

def get_channel_from_filename(data_filename):
    """
    Args:
        data_filename (str)
        
    Returns:
        int
    """
    channel_str = data_filename.lstrip('channel_').rstrip('.dat')
    return int(channel_str)


def append_files(input_filename, output_filename):
    """
    Appends input_filename onto the end of output_filename.
    
    Args:
        input_filename, output_filename (str): full paths to files
    """
    input_file = open(input_filename, 'r')    
    output_file = open(output_filename, 'a')
    while True:
        data = input_file.readline()
        if data and data.strip():
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
        processed_subdirs.append(base_data_dir)
    else:
        # Recurse through any directories which don't have a labels.dat

        # Get just the names of the directories within base_data_dir
        # Taken from http://stackoverflow.com/a/142535/732596
        subdirs = os.walk(base_data_dir).next()[1]
        for subdir in subdirs:
            full_subdir = os.path.join(base_data_dir, subdir)                
            processed_subdirs.extend(get_all_data_dirs(full_subdir))

    return processed_subdirs


def main():
    args = setup_argparser()
    
    template_labels = TemplateLabels(args.template_labels_filename)
    
    data_directories = get_all_data_dirs(args.base_data_dir)
    
    # First find the correct ordering for the datasets:
    datasets = []
    for data_dir in data_directories:
        datasets.append(Dataset(data_dir))
    datasets.sort(key=lambda dataset: dataset.first_timestamp)
    
    check_not_overlapping(datasets)
    
    # Now merge the datasets
    for dataset in datasets:        
        labels_map = template_labels.assimilate_and_get_map(dataset.data_dir)
        
        for data_filename in get_data_filenames(dataset.data_dir):
            input_channel = get_channel_from_filename(data_filename)
            input_filename = os.path.join(dataset.data_dir, data_filename)
            output_channel = labels_map[input_channel]
            output_filename = os.path.join(args.output_dir,
                                           'channel_{:d}.dat'
                                           .format(output_channel))
            append_files(input_filename, output_filename)

    template_labels.write_to_disk(args.output_dir)

if __name__=="__main__":
    main()