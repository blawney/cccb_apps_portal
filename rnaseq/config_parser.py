import os
from ConfigParser import SafeConfigParser

CONFIG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.cfg')

def parse_config():
    with open(CONFIG_FILE) as cfg_handle:
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
