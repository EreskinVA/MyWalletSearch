/*
 * Precompiled Header
 * This file is included FIRST in all source files to ensure
 * Windows compatibility macros are defined before any Windows headers.
 */

#ifndef STDAFX_H
#define STDAFX_H

// Windows compatibility - MUST be first, before ANY other includes
#ifdef _WIN32
// Force clear any previous definitions - do this BEFORE any includes
#undef NOMINMAX
#undef WIN32_LEAN_AND_MEAN
#undef STRICT
#undef min
#undef max

// Define compatibility macros BEFORE any Windows headers
#define NOMINMAX 1
#define WIN32_LEAN_AND_MEAN 1
#define STRICT 1

// Suppress warnings about macro redefinitions and typedef issues in Windows SDK headers
#pragma warning(push)
#pragma warning(disable: 4005) // macro redefinition
#pragma warning(disable: 4091) // typedef ignored
#pragma warning(disable: 4668) // '__cplusplus' is not defined as a preprocessor macro

// Include Windows headers with correct macro definitions
// This ensures all Windows SDK types (DWORD64, LARGE_INTEGER, etc.) are defined correctly
#include <windows.h>
#include <intrin.h>

#pragma warning(pop)
#endif

// Standard C++ headers
#include <cstdint>
#include <string>
#include <vector>
#include <algorithm>

#endif // STDAFX_H

