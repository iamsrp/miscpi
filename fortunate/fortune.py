"""

"""


import logging as LOG
import os
import random

# ----------------------------------------------------------------------

class Fortune():
    """
    A service which pulls out text from the fortune files and delivers it to the
    user.
    """
    def __init__(self,
                 fortunes_dir="/usr/share/games/fortunes",
                 max_length  =200):
        """
        @see Service.__init__()
        
        :type fortunes_dir: str
        :param fortunes_dir:
            The location of the fortune data files.
        :type max_length: int
        :param max_length:
            The maximum length of a selected fortune, in bytes.
        """
        self._dir     = fortunes_dir
        self._max_len = int(max_length)


    def pick(self):
        """
        Choose a random fortune. This is the meat of this class.
        """
        # We do this all from scratch each time since it's not _that_ expensive
        # and it means we don't have to restart anything when new files are
        # added. We have a list of filenames and the start and end of their data
        # as part of the total count.
        #
        # We are effectively concatenating the files here so as to avoid
        # bias. Consider: if you have two files, with one twice the size of the
        # other, if we picked a random fortune from a random file then then
        # fortunes in the smallee file would be twice as likely to come up as
        # ones in the bigger one.
        file_info = []
        total_size = 0
        for (subdir, _, files) in os.walk(self._dir, followlinks=True):
            for filename in files:
                # The fortune files have an associated .dat file, this means we
                # can identify them by looking for that .dat file.
                path = os.path.join(subdir, filename)
                dat_path = path + '.dat'
                LOG.debug("Candidate: %s %s", path, dat_path)
                if os.path.exists(dat_path):
                    # Open it to make sure can do so
                    try:
                        with open(path, 'rt'):
                            # Get the file length to use it to accumulate into
                            # our running counter, and to compute the file-
                            # specifc stats.
                            stat = os.stat(path)

                            # The start of the file is the current total_size
                            # and the end is that plus the file size
                            start = total_size
                            total_size += stat.st_size
                            end = total_size
                            file_info.append((path, start, end))
                            LOG.debug("Adding %s[%d:%d]", path, start, end)
                    except Exception as e:
                        LOG.debug("Failed to add %s: %s", path, e)


        # Keep trying this until we get something, or until we give up. Most of
        # the time we expect this to work on the first go unless something weird
        # is going on.
        for tries in range(10):
            LOG.debug("Try #%d", tries)

            # Now that we have a list of files, pick one at random by choosing a
            # point somewhere in there
            offset = random.randint(0, total_size)
            LOG.debug("Picked offset %d", offset)

            # Now we look for the file which contains that offset
            for (filename, start, end) in file_info:
                if start <= offset < end:
                    with open(filename, 'rt') as fh:
                        # Jump to the appropriate point in the file, according to
                        # the offset (relative to the files's start in the overall
                        # set)
                        seek_offset = offset - start
                        if seek_offset > 0:
                            fh.seek(seek_offset)

                        try:
                            # Now look for the bracketing '%'s. Read in a nice big
                            # chunk and hunt for it in there.
                            chunk = fh.read(min(10 * self._max_len, 1024 * 1024))

                            # The file could start with a bracketer and we want
                            # to catch that
                            if seek_offset == 0 and chunk.startswith('%\n'):
                                s = 2
                            else:
                                s = chunk.index('\n%\n') + 3

                            # Now look for the end. A properly-formed file
                            # should have a '%\n' as its last line.
                            e = chunk.index('\n%\n', s)

                            # We found a match. Is it small enough?
                            LOG.debug("Found section %s[%d:%d]", filename, s, e)
                            if (e - s) > self._max_len:
                                # Nope, go around and try again
                                break
                            else:
                                # Yes!
                                return chunk[s:e]

                        except ValueError:
                            # Find to match so give up and go around again
                            break

        # If we got here then we gave up trying
        return None



if __name__ == "__main__":
    fortune = Fortune()
    print(fortune.pick())
