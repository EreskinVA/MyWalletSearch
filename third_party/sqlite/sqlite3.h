#pragma once

// Minimal SQLite3 header for VanitySearch on Windows.
// Purpose:
// - Fix MSVC builds when system sqlite3 development headers are not installed
// - Provide only the subset of SQLite API that VanitySearch uses
//
// On Windows we pair this header with `sqlite3_dynamic.cpp`, which loads sqlite3.dll
// at runtime (no sqlite3.lib needed at link time).
//
// If you prefer linking against a system-provided SQLite, you can:
// - Remove `third_party/sqlite` from include paths, and
// - Provide your own sqlite3.h + sqlite3.lib in project settings.

#ifdef __cplusplus
extern "C" {
#endif

typedef struct sqlite3 sqlite3;
typedef struct sqlite3_stmt sqlite3_stmt;

typedef void (*sqlite3_destructor_type)(void*);

#ifndef SQLITE_API
  #if defined(_WIN32)
    #define SQLITE_API __cdecl
  #else
    #define SQLITE_API
  #endif
#endif

// Result codes (subset)
#ifndef SQLITE_OK
#define SQLITE_OK 0
#endif

#ifndef SQLITE_ERROR
#define SQLITE_ERROR 1
#endif

#ifndef SQLITE_ROW
#define SQLITE_ROW 100
#endif

#ifndef SQLITE_DONE
#define SQLITE_DONE 101
#endif

// Open flags (subset)
#ifndef SQLITE_OPEN_READONLY
#define SQLITE_OPEN_READONLY 0x00000001
#endif

#ifndef SQLITE_OPEN_FULLMUTEX
#define SQLITE_OPEN_FULLMUTEX 0x00010000
#endif

// Destructor behaviour for bind APIs
#ifndef SQLITE_STATIC
#define SQLITE_STATIC ((sqlite3_destructor_type)0)
#endif

int SQLITE_API sqlite3_open_v2(
  const char *filename,
  sqlite3 **ppDb,
  int flags,
  const char *zVfs
);

const char *SQLITE_API sqlite3_errmsg(sqlite3 *db);

int SQLITE_API sqlite3_close(sqlite3 *db);

int SQLITE_API sqlite3_prepare_v2(
  sqlite3 *db,
  const char *zSql,
  int nByte,
  sqlite3_stmt **ppStmt,
  const char **pzTail
);

int SQLITE_API sqlite3_step(sqlite3_stmt *pStmt);

int SQLITE_API sqlite3_finalize(sqlite3_stmt *pStmt);

long long SQLITE_API sqlite3_column_int64(sqlite3_stmt *pStmt, int iCol);

const unsigned char *SQLITE_API sqlite3_column_text(sqlite3_stmt *pStmt, int iCol);

int SQLITE_API sqlite3_bind_text(
  sqlite3_stmt *pStmt,
  int i,
  const char *zData,
  int nData,
  sqlite3_destructor_type xDel
);

#ifdef __cplusplus
}  // extern "C"
#endif


