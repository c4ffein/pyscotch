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

/*
 * Scotch error-message capture
 *
 * Scotch deliberately leaves SCOTCH_errorPrint / SCOTCH_errorPrintW /
 * SCOTCH_errorProg unsuffixed so that host programs can provide their own
 * implementations. When this library is dlopen'd with RTLD_GLOBAL *before*
 * libscotcherr, the dynamic linker resolves Scotch's error calls here and
 * the messages accumulate in a buffer that Python reads (and clears) when
 * it raises an exception — instead of being lost on stderr.
 */

#include <stdarg.h>
#include <string.h>

#define PYSCOTCH_ERR_MAX 4096

static char pyscotch_err_buf[PYSCOTCH_ERR_MAX];

static void pyscotch_err_append(const char* prefix, const char* fmt, va_list ap) {
    size_t len = strlen(pyscotch_err_buf);
    if (len > 0 && len < PYSCOTCH_ERR_MAX - 1) {
        pyscotch_err_buf[len++] = '\n';
        pyscotch_err_buf[len] = '\0';
    }
    if (len < PYSCOTCH_ERR_MAX - 1) {
        snprintf(pyscotch_err_buf + len, PYSCOTCH_ERR_MAX - len, "%s", prefix);
        len = strlen(pyscotch_err_buf);
    }
    if (len < PYSCOTCH_ERR_MAX - 1) {
        vsnprintf(pyscotch_err_buf + len, PYSCOTCH_ERR_MAX - len, fmt, ap);
    }
}

/* Read the accumulated messages (empty string when none) */
const char* pyscotch_err_get(void) {
    return pyscotch_err_buf;
}

/* Reset the buffer */
void pyscotch_err_clear(void) {
    pyscotch_err_buf[0] = '\0';
}

void SCOTCH_errorPrint(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    pyscotch_err_append("ERROR: ", fmt, ap);
    va_end(ap);
}

void SCOTCH_errorPrintW(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    pyscotch_err_append("WARNING: ", fmt, ap);
    va_end(ap);
}

/* Scotch calls this with the program name; nothing to do for a library */
void SCOTCH_errorProg(const char* progstr) {
    (void)progstr;
}
