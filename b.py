#!/usr/bin/env python
import os
import sys
import time

import settings

def run_command(cmd):
    print 'Running "{0}"'.format(cmd)
    os.system(cmd)

def main(argv):
    # TODO: -f, --force parameter
    
    if settings.DEBUG:
        print "WARNING: DEBUG is ON!!!"
        print "WARNING: DEBUG is ON!!!"
        sys.stdout.flush()
        time.sleep(1)

    run_command("./node_modules/grunt-cli/bin/grunt")
    run_command("python manage.py collectstatic --noinput")
    run_command("python manage.py compilemessages");

    # TODO: no "--all" if --force
    run_command("python manage.py compile_templates -v 0 --all --noinput")


if __name__ == "__main__":
    main(sys.argv)
