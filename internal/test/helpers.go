package test

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

// Must panics if err is not nil, otherwise returns v.
func Must[T any](v T, err error) T {
	if err != nil {
		panic(err)
	}
	return v
}

// ReadFile reads a file relative to the caller's source file location.
// Test-only helper: every call site in this codebase passes hardcoded
// literal path segments (testdata fixture names), never external input.
func ReadFile(path ...string) string {
	_, file, _, _ := runtime.Caller(1)
	filePath := filepath.Join(append([]string{filepath.Dir(file)}, path...)...)
	fileBytes := Must(os.ReadFile(filePath)) // #nosec G304
	return string(fileBytes)
}

// CreateTempFile creates a temporary file with the given name and content.
// The file is automatically cleaned up when the test completes.
// Returns the absolute path to the created file.
func CreateTempFile(t *testing.T, name, content string) string {
	t.Helper()
	tmpDir := t.TempDir()
	filePath := filepath.Join(tmpDir, name)
	if err := os.WriteFile(filePath, []byte(content), 0o600); err != nil {
		t.Fatalf("failed to create temp file %s: %v", name, err)
	}
	return filePath
}
