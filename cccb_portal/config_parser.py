import os
from ConfigParser import SafeConfigParser

def parse_config(config_file):
    with open(config_file) as cfg_handle:
        parser = SafeConfigParser()
        parser.readfp(cfg_handle)
        defaults = parser.defaults()
        d = {}
        for key, val in defaults.items():
            vals = val.split(',')
            if len(vals) > 1:
                d[key] = [x.strip() for x in vals if len(x.strip()) > 0]
            else:
                d[key] = val
        return d
