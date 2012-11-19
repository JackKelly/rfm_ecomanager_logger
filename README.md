# Python front-end for the rfm_edf_ecomanager RF base unit

If you are using Linux and you get a "permission denied" error when trying
to access the serial port then you'll need to change your udev rules.
For example, try creating the following file:

 file: /etc/udev/rules.d/nanode.rules
 
 SUBSYSTEM!="usb_device", ACTION!="add", GOTO="nanode_rules_end"
 ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="660", GROUP:="plugdev" 
 LABEL="nanode_rules_end"