#!/usr/bin/python
from __future__ import print_function, division
import argparse, os

def setup_argparser():
    # Process command line _args
    parser = argparse.ArgumentParser(description='Merge datasets')
   
    parser.add_argument('--template-labels-filename', type=str,
                        help='The labels file to attempt to conform all input'
                        ' datasets to.')
    
    parser.add_argument('--output-dir', type=str)
        
    return parser.parse_args()


class Dataset(object):
    def __init__(self, first_timestamp, last_timestamp, data_dir):
        self.first_timestamp = first_timestamp
        self.last_timestamp = last_timestamp
        self.data_dir = data_dir
        

def get_timestamp_range(data_dir):
    """
    Args:
        data_dir (str)
        
    Returns:
        first_timestamp (float), last_timestamp (float)
    """
    
    # For each channel_??.dat file:
    #  Load first line, load last line...


def load_labels_file(labels_filename):
    """
    Args:
        labels_filename (str)
        
    Returns:
        dict mapping channel number to label
    """

class TemplateLabels(object):
    
    def __init__(self, labels_file):
        self.labels = load_labels_file(labels_file)

    def assimilate_and_get_map(self, source_labels_filename):
        """
        If source_labels contains any labels not in self.labels
        then add those labels to self.labels and return a mapping
        from source labels to template labels.
        
        Args:
            source_labels_filename (str)
            
        Returns:
            dict mapping from source labels index to template labels index.
            e.g.
                {1: 1,  2: 3,  3: 2}
                maps source labels 1, 2 and 3 to template labels 1, 3 and 2
        """
        source_labels = load_labels_file(source_labels_filename)

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

def append_data(input_filename, output_filename):
    """
    Appends input_filename onto the end of output_filename.
    
    Args:
        input_filename, output_filename (str)
    """


def main():
    args = setup_argparser()
    
    template_labels = TemplateLabels(args.template_labels_filename)
    
    # TODO: data_directories = list of full directories
    
    # First find the correct ordering for the datasets:
    datasets = []
    for data_dir in data_directories:
        first_timestamp, last_timestamp = get_timestamp_range(data_dir)
        datasets.append(Dataset(first_timestamp, last_timestamp, data_dir))
    datasets.sort(key=lambda dataset: dataset.first_timestamp)
    
    check_not_overlapping(datasets)
    
    # Now merge the datasets
    for dataset in datasets:
        labels_filename = os.path.join(dataset.data_dir, 'labels.dat')
        labels_map = template_labels.assimilate_and_get_map(labels_filename)
        
        for data_filename in get_data_filenames(dataset.data_dir):
            input_channel = get_channel_from_filename(data_filename)
            input_filename = os.path.join(dataset.data_dir, data_filename)
            output_channel = labels_map[input_channel]
            output_filename = os.path.join(args.output_dir,
                                           'channel_{:d}.dat'
                                           .format(output_channel))
            append_data(input_filename, output_filename)

    template_labels.write_to_disk(args.output_dir)

if __name__=="__main__":
    main()