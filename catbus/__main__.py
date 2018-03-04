import os
import sys

if __name__ == '__main__':
    from . import browser, client
    endpoint = os.environ['CATBUS_URL']
    sys.exit(browser.cli(client.Client(), endpoint, sys.argv[1:]))
    
