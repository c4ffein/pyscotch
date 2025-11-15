"""
NOT PORTED: external/scotch/src/check/test_common_file_compress.c

File compression utilities - INTERNAL FILE API

REASON FOR NOT PORTING:
This test uses Scotch's internal file compression API, which is NOT part of
the public API exposed in scotch.h.

The test uses internal functions from common_file.h and common_file_compress.h:
- fileBlockInit() - Initialize file block
- fileBlockOpen() - Open files with compression support
- fileBlockClose() - Close files and finish compression
- fileBlockFile() - Get FILE* from file block
- File structure - Internal file descriptor

These are internal utilities that Scotch uses for transparent compression/
decompression of graph files. They are not exposed to external users.

PyScotch users should use Python's standard file I/O or compression libraries
(gzip, bz2, lzma) when working with compressed files.
"""

# No tests - this file documents why test_common_file_compress.c is not ported
