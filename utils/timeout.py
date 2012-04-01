import subprocess, threading

class Command(object):
    '''
    Modified version of https://gist.github.com/1306188

    Example:
    command = Command('latex -interaction=batchmode test.tex')
    if command.run(timeout=5):
        raise Exception('Error')
    else:
        return 'OK!'

    ----------------------------
    
    Enables to run subprocess commands in a different thread
    with TIMEOUT option!

    Based on jcollado's solution:
    http://stackoverflow.com/questions/1191374/subprocess-with-timeout/4825933#4825933
    '''
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None

    def run(self, timeout=None, **kwargs):
        def target(**kwargs):
            self.process = subprocess.Popen(self.cmd, **kwargs)
            self.process.communicate()

        thread = threading.Thread(target=target, kwargs=kwargs)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            print 'Terminating process: ', self.cmd
            self.process.terminate()
            thread.join()
            return -2

        if not self.process:
            return -1
        return self.process.returncode

def run_command(cmd, timeout=5, shell=True, **kwargs):
    # shell=True makes this method vulnerable to shell injection!
    # DO NOT execute any commands constructed from external input!
    command = Command(cmd)
    return command.run(timeout, shell=shell, **kwargs)
