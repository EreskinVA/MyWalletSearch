/*
 * Precompiled Header
 * This file is included FIRST in all source files to ensure
 * Windows compatibility macros are defined before any Windows headers.
 */

#ifndef STDAFX_H
#define STDAFX_H

// Windows compatibility - MUST be first, before ANY other includes
#ifdef _WIN32
// Force clear any previous definitions
#undef NOMINMAX
#undef WIN32_LEAN_AND_MEAN
#undef STRICT
#undef min
#undef max

// Define compatibility macros
#define NOMINMAX 1
#define WIN32_LEAN_AND_MEAN 1
#define STRICT 1
#endif

// Standard C++ headers
#include <cstdint>
#include <string>
#include <vector>
#include <algorithm>

#endif // STDAFX_H

