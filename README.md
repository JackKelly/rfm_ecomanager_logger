Python front-end for the [rfm_edf_ecomanager RF base unit](/JackKelly/rfm_edf_ecomanager/) which 
makes it relatively easy to add, remove and edit transmitters and also to log power consumption data
to a set of log files in the same format as used by [MIT's REDD project](http://redd.csail.mit.edu/).

# Manual

* Please see [the wiki](https://github.com/JackKelly/rfm_ecomanager_logger/wiki) for a guide to using this code.

### Related projects

* [rfm_edf_ecomanager RF base unit](https://github.com/JackKelly/rfm_edf_ecomanager/) Code which runs
on a Nanode / Arduino and the rfm_ecomanager_logger talks to.
* [babysitter](https://github.com/JackKelly/babysitter) Keeps tabs on a logging process (like rfm_ecomanager_logger) and sends an
email if problems are detected.
* [powerstats](https://github.com/JackKelly/powerstats) Create simple statistics from power data text files.  Mostly useful to check 
that transmitters are behaving themselves.

### Permission denied error

If you are using Linux and you get a "permission denied" error when trying
to access the serial port then you'll need to change your udev rules.
For example, try creating the following file:

```file: /etc/udev/rules.d/nanode.rules```

```
SUBSYSTEM!="usb_device", ACTION!="add", GOTO="nanode_rules_end"
ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="660", GROUP:="plugdev" 
LABEL="nanode_rules_end"
```
