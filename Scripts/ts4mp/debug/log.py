import os
import time
from ts4mp.core.mp_utils import get_sims_documents_directory

DEBUG_MODE = True


def ts4mp_log(filename, string, force=False):
    global DEBUG_MODE

    if DEBUG_MODE is False and force is False:
        return

    if filename == "locks":
        return

    logs_directory = "{}ts4mp_logs/".format(get_sims_documents_directory())

    if not os.path.exists(logs_directory):
        os.makedirs(logs_directory)

    with open("{}{}.txt".format(logs_directory, filename), 'a') as stream:
        stream.write("{} - {} {}".format(time.ctime(), str(string),  "\n"))
