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
// Force these macros to be defined BEFORE any Windows headers are included
// Use #undef first to clear any previous definitions
#undef NOMINMAX
#undef WIN32_LEAN_AND_MEAN
#undef STRICT

// Now define them
#define NOMINMAX 1
#define WIN32_LEAN_AND_MEAN 1
#define STRICT 1

// Prevent min/max macro definitions
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif
#endif

#endif // WINDOWSCOMPATH

