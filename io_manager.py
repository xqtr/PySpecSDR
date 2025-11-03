import os

PIPE_PATH = "/tmp/sdrpipe"
PIPE_FILE = None
USE_PIPE = False


# Pipe Functions
def create_pipe():
    global PIPE_PATH
    """Create a named pipe for output."""
    try:
        os.mkfifo(PIPE_PATH)
    except FileExistsError:
        pass  # Pipe already exists


def open_file_pipe():
    fifo = open(PIPE_PATH, 'wb', os.O_NONBLOCK)
    return fifo


def write_to_pipe(fifof,data,stdscr):
    """Write audio data to the named pipe."""
    if data.dtype != np.int16:
        data = np.int16(data * 32767)
    fifof.write(data)


def close_file_pipe(fifo):
    fifo.close()


def clean_pipe(signum, frame):
    """Cleanup function to remove the named pipe."""
    if os.path.exists(PIPE_PATH):
        os.unlink(PIPE_PATH)
