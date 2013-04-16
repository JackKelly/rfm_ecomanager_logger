#!/usr/bin/python
from __future__ import print_function, division
import argparse, os

# TODO:
# * allow template-labels-filename to including alternative names
#   for the same channel.  e.g.
#   1 aggregate %OR agg

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

def append_data(input_filename, output_filename):
    """
    Appends input_filename onto the end of output_filename.
    
    Args:
        input_filename, output_filename (str)
    """


def main():
    args = setup_argparser()
    
    template_labels = TemplateLabels(args.template_labels_filename)
    
    # TODO: data_directories = list of full directories.
    # recursive.  For each dir: if it has a labels.dat file then
    # it's a data dir.  Else if it contains a directory the recurse
    # through the dir structure.
    
    # First find the correct ordering for the datasets:
    datasets = []
    for data_dir in data_directories:
        first_timestamp, last_timestamp = get_timestamp_range(data_dir)
        datasets.append(Dataset(first_timestamp, last_timestamp, data_dir))
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
            append_data(input_filename, output_filename)

    template_labels.write_to_disk(args.output_dir)

if __name__=="__main__":
    main()