// Runtime-loaded SQLite shim for Windows builds of VanitySearch.
// Exports a minimal subset of sqlite3_* symbols used by VanitySearch and
// forwards them to sqlite3.dll resolved via LoadLibrary/GetProcAddress.
//
// This avoids requiring sqlite3.h/sqlite3.lib at build time in MSVC projects.

#if defined(_WIN32)

#include "sqlite3.h"

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>

#include <mutex>
#include <string>

namespace {

std::once_flag g_once;
HMODULE g_sqlite = nullptr;
std::string g_lastErr;

template <typename T>
T LoadFn(const char *name) {
  FARPROC p = GetProcAddress(g_sqlite, name);
  return reinterpret_cast<T>(p);
}

bool EnsureLoaded() {
  std::call_once(g_once, []() {
    g_sqlite = LoadLibraryA("sqlite3.dll");
    if (!g_sqlite) {
      g_lastErr = "sqlite3.dll not found (put sqlite3.dll рядом с VanitySearch.exe или добавьте в PATH)";
      return;
    }

    // Validate that required functions exist; if not, unload and fail.
    // We don't store them here (we store per-function statics below), but this catches early.
    const char *required[] = {
      "sqlite3_open_v2",
      "sqlite3_errmsg",
      "sqlite3_close",
      "sqlite3_prepare_v2",
      "sqlite3_step",
      "sqlite3_finalize",
      "sqlite3_column_int64",
      "sqlite3_column_text",
      "sqlite3_bind_text",
    };
    for (const char *fn : required) {
      if (!GetProcAddress(g_sqlite, fn)) {
        g_lastErr = std::string("sqlite3.dll missing required symbol: ") + fn;
        FreeLibrary(g_sqlite);
        g_sqlite = nullptr;
        return;
      }
    }
  });

  return g_sqlite != nullptr;
}

} // namespace

extern "C" {

int SQLITE_API sqlite3_open_v2(const char *filename, sqlite3 **ppDb, int flags, const char *zVfs) {
  if (ppDb) *ppDb = nullptr;
  if (!EnsureLoaded()) return SQLITE_ERROR;
  using Fn = int (SQLITE_API *)(const char*, sqlite3**, int, const char*);
  static Fn fn = nullptr;
  if (!fn) fn = LoadFn<Fn>("sqlite3_open_v2");
  if (!fn) return SQLITE_ERROR;
  return fn(filename, ppDb, flags, zVfs);
}

const char *SQLITE_API sqlite3_errmsg(sqlite3 *db) {
  if (!EnsureLoaded()) return g_lastErr.empty() ? "sqlite3.dll not loaded" : g_lastErr.c_str();
  using Fn = const char * (SQLITE_API *)(sqlite3*);
  static Fn fn = nullptr;
  if (!fn) fn = LoadFn<Fn>("sqlite3_errmsg");
  if (!fn) return "sqlite3_errmsg unavailable";
  return fn(db);
}

int SQLITE_API sqlite3_close(sqlite3 *db) {
  if (!EnsureLoaded()) return SQLITE_ERROR;
  using Fn = int (SQLITE_API *)(sqlite3*);
  static Fn fn = nullptr;
  if (!fn) fn = LoadFn<Fn>("sqlite3_close");
  if (!fn) return SQLITE_ERROR;
  return fn(db);
}

int SQLITE_API sqlite3_prepare_v2(sqlite3 *db, const char *zSql, int nByte, sqlite3_stmt **ppStmt, const char **pzTail) {
  if (ppStmt) *ppStmt = nullptr;
  if (!EnsureLoaded()) return SQLITE_ERROR;
  using Fn = int (SQLITE_API *)(sqlite3*, const char*, int, sqlite3_stmt**, const char**);
  static Fn fn = nullptr;
  if (!fn) fn = LoadFn<Fn>("sqlite3_prepare_v2");
  if (!fn) return SQLITE_ERROR;
  return fn(db, zSql, nByte, ppStmt, pzTail);
}

int SQLITE_API sqlite3_step(sqlite3_stmt *pStmt) {
  if (!EnsureLoaded()) return SQLITE_ERROR;
  using Fn = int (SQLITE_API *)(sqlite3_stmt*);
  static Fn fn = nullptr;
  if (!fn) fn = LoadFn<Fn>("sqlite3_step");
  if (!fn) return SQLITE_ERROR;
  return fn(pStmt);
}

int SQLITE_API sqlite3_finalize(sqlite3_stmt *pStmt) {
  if (!EnsureLoaded()) return SQLITE_ERROR;
  using Fn = int (SQLITE_API *)(sqlite3_stmt*);
  static Fn fn = nullptr;
  if (!fn) fn = LoadFn<Fn>("sqlite3_finalize");
  if (!fn) return SQLITE_ERROR;
  return fn(pStmt);
}

long long SQLITE_API sqlite3_column_int64(sqlite3_stmt *pStmt, int iCol) {
  if (!EnsureLoaded()) return 0;
  using Fn = long long (SQLITE_API *)(sqlite3_stmt*, int);
  static Fn fn = nullptr;
  if (!fn) fn = LoadFn<Fn>("sqlite3_column_int64");
  if (!fn) return 0;
  return fn(pStmt, iCol);
}

const unsigned char *SQLITE_API sqlite3_column_text(sqlite3_stmt *pStmt, int iCol) {
  if (!EnsureLoaded()) return nullptr;
  using Fn = const unsigned char * (SQLITE_API *)(sqlite3_stmt*, int);
  static Fn fn = nullptr;
  if (!fn) fn = LoadFn<Fn>("sqlite3_column_text");
  if (!fn) return nullptr;
  return fn(pStmt, iCol);
}

int SQLITE_API sqlite3_bind_text(sqlite3_stmt *pStmt, int i, const char *zData, int nData, sqlite3_destructor_type xDel) {
  if (!EnsureLoaded()) return SQLITE_ERROR;
  using Fn = int (SQLITE_API *)(sqlite3_stmt*, int, const char*, int, sqlite3_destructor_type);
  static Fn fn = nullptr;
  if (!fn) fn = LoadFn<Fn>("sqlite3_bind_text");
  if (!fn) return SQLITE_ERROR;
  return fn(pStmt, i, zData, nData, xDel);
}

} // extern "C"

#else

// Non-Windows builds should use system SQLite (Makefile: -lsqlite3).
// This translation unit is intentionally empty on non-Windows.
int vanitysearch_sqlite3_dynamic_dummy = 0;

#endif


