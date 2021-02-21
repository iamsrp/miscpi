#!/usr/bin/env python3
"""
Read fortunes and display them on an eink display.
"""

from   fortune import Fortune
from   pink    import Pink, InkyDisplay

import socket
import time

def main():
    # What and how we print to the display
    fortune = Fortune(max_length=800)
    pink    = Pink(InkyDisplay())
    max_cols = 36

    # Do this forever
    while True:
        text = fortune.pick()
        if not text:
            continue
        text = text.split('\n')
        line_length = max(len(line) for line in text)
        if line_length > max_cols:
            max_length = line_length // 2
        else:
            max_length = max_cols

        lines = []
        for line in text:
            line = line.strip()
            if not line:
                continue
            line = ' '.join(line.split())
            if len(line) > max_length:
                line1 = ''
                line2 = ''
                for word in line.split():
                    if len(line1) < max_length:
                        line1 = '%s%s ' % (line1, word)
                    else:
                        line2 = '%s%s ' % (line2, word)
                if line1:
                    lines.append(line1.strip()) 
                if line2:
                    lines.append(line2.strip())
            else:
                lines.append(line)
        text = '\n'.join(lines)

        print('=' * 30)
        print(text)
        pink.write(text)

        # And wait 3 mins before reading again
        until = time.time() + 3 * 60
        while time.time() < until:
            time.sleep(0.001)

if __name__ == "__main__":
    main()
