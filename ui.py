def draw_clearheader(stdscr):
    max_height, max_width = stdscr.getmaxyx()
    stdscr.addstr(0, 0, " "*(max_width-1))
    stdscr.addstr(1, 0, " "*(max_width-1))
