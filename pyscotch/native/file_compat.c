/*
 * PyScotch File Compatibility Layer
 *
 * Provides FILE* operations compiled with the SAME toolchain/libc as Scotch,
 * guaranteeing ABI compatibility (no struct layout mismatches, LFS issues, etc.)
 *
 * V0: Minimal wrappers - just fopen/fclose
 *
 * Usage from Python (via ctypes):
 *   compat = ctypes.CDLL("libpyscotch_compat.so")
 *   file_ptr = compat.pyscotch_fopen(b"/path/file.grf", b"r")
 *   # ... use file_ptr with Scotch functions ...
 *   compat.pyscotch_fclose(file_ptr)
 */

#include <stdio.h>
#include <errno.h>

/*
 * Open a file using C's fopen()
 *
 * This is compiled with the SAME compiler/flags as Scotch, ensuring
 * the FILE* structure layout matches exactly.
 *
 * Returns: FILE* pointer on success, NULL on failure (sets errno)
 */
FILE* pyscotch_fopen(const char* path, const char* mode) {
    return fopen(path, mode);
}

/*
 * Close a file using C's fclose()
 *
 * Returns: 0 on success, EOF on failure
 */
int pyscotch_fclose(FILE* stream) {
    if (stream == NULL) {
        return EOF;
    }
    return fclose(stream);
}

/*
 * Get current errno value
 *
 * Helper for Python to get errno after failed fopen
 * (ctypes.get_errno() might not work if using different libc)
 *
 * Returns: Current errno value
 */
int pyscotch_get_errno(void) {
    return errno;
}
