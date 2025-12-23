/*
 * Windows Compatibility Header
 * This file must be included FIRST in all source files to prevent
 * conflicts with Windows SDK headers.
 * 
 * It defines NOMINMAX and WIN32_LEAN_AND_MEAN before any Windows
 * headers are included, preventing conflicts with min/max macros
 * and reducing the number of included headers.
 */

#ifndef WINDOWSCOMPATH
#define WINDOWSCOMPATH

// Windows-specific definitions must come BEFORE any Windows headers
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
// Prevent conflicts with Windows SDK definitions
#ifndef STRICT
#define STRICT
#endif
#endif

#endif // WINDOWSCOMPATH

