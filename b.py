import os
import settings

def run_command(cmd):
    print 'Running "{0}"'.format(cmd)
    os.system(cmd)

def main(argv):
    # TODO: -f, --force parameter
    
    if settings.DEBUG:
        print "WARNING: DEBUG is ON!!!"
        print "WARNING: DEBUG is ON!!!"

    run_command("python manage.py collectstatic --noinput")

    # TODO: no "--all" if --force
    run_command("python manage.py compile_templates -v 2 --all --noinput")


if __name__ == "__main__":
    import sys
    main(sys.argv)