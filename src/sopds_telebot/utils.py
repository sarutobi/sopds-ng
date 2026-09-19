import logging
import os
import signal
import sys

from opds_catalog.config import catalog_config

logger = logging.getLogger(__name__)


def writepid(pid_file):
    """
    Write the process ID to disk.
    """
    try:
        with open(pid_file, "w") as fp:
            fp.write(str(os.getpid()))
    except Exception as e:
        logger.error(f"Failed to write PID file {pid_file}: {e}")


def daemonize():
    """
    Detach from the terminal and continue as a daemon.
    """
    # swiped from twisted/scripts/twistd.py
    # See http://www.erlenstar.demon.co.uk/unix/faq_toc.html#TOC16
    if os.fork():  # launch child and...
        os._exit(0)  # kill off parent
    os.setsid()
    if os.fork():  # launch child and...
        os._exit(0)  # kill off parent again.
    os.umask(0)

    try:
        std_in = open("/dev/null", "r")
        std_out = open(catalog_config.BOT_LOG_FILE, "a+")
        os.dup2(std_in.fileno(), sys.stdin.fileno())
        os.dup2(std_out.fileno(), sys.stdout.fileno())
        os.dup2(std_out.fileno(), sys.stderr.fileno())

        os.close(std_in.fileno())
        os.close(std_out.fileno())
    except Exception as e:
        logger.error(f"Failed to daemonize: {e}")


def kill_process(pid):
    """
    Kill process by PID.
    """
    try:
        os.kill(int(pid), signal.SIGTERM)
        return True
    except (OSError, ValueError) as e:
        logger.error(f"Error stopping process {pid}: {e}")
        return False
