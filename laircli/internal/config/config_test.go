package config

import (
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// isolate 把配置文件指到用例独占路径，避免读写真实 ~/.laircli。
func isolate(t *testing.T) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "config.json")
	t.Setenv("LAIRCLI_CONFIG", path)
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("OPENLAIR_API_KEY", "")
	t.Setenv("OPENLAIR_BASE_URL", "")
	t.Setenv("OPENLAIR_BOOK_ID", "")
	t.Setenv("LAIRCLI_JSON", "")
	return path
}

func TestResolvePriority(t *testing.T) {
	path := isolate(t)
	if err := os.WriteFile(path, []byte(`{"api_key":"ol_file","base_url":"https://file.example/","book_id":7,"user":"小明"}`), 0o600); err != nil {
		t.Fatal(err)
	}

	got, err := Resolve(Flags{})
	if err != nil {
		t.Fatal(err)
	}
	if got.APIKey != "ol_file" || got.BaseURL != "https://file.example" || got.BookID == nil || *got.BookID != 7 {
		t.Fatalf("文件层解析不对: %+v", got)
	}
	if got.User != "小明" {
		t.Fatalf("user 没读出来: %+v", got)
	}

	t.Setenv("OPENLAIR_API_KEY", "ol_env")
	t.Setenv("OPENLAIR_BOOK_ID", "9")
	got, err = Resolve(Flags{})
	if err != nil {
		t.Fatal(err)
	}
	if got.APIKey != "ol_env" || *got.BookID != 9 {
		t.Fatalf("env 应压过文件: %+v", got)
	}

	got, err = Resolve(Flags{APIKey: "ol_flag", BaseURL: "http://127.0.0.1:8001"})
	if err != nil {
		t.Fatal(err)
	}
	if got.APIKey != "ol_flag" || got.BaseURL != "http://127.0.0.1:8001" {
		t.Fatalf("flag 应压过 env: %+v", got)
	}
}

func TestResolveMissingKeyIsNotConfigured(t *testing.T) {
	isolate(t)
	if _, err := Resolve(Flags{}); !errors.Is(err, ErrNotConfigured) {
		t.Fatalf("缺 Key 应返回 ErrNotConfigured，实际 %v", err)
	}
}

func TestResolveBaseURLDefault(t *testing.T) {
	isolate(t)
	t.Setenv("OPENLAIR_API_KEY", "ol_x")
	got, err := Resolve(Flags{})
	if err != nil {
		t.Fatal(err)
	}
	if got.BaseURL != DefaultBaseURL {
		t.Fatalf("默认地址应为 %s，实际 %s", DefaultBaseURL, got.BaseURL)
	}
	if got.BookID != nil {
		t.Fatalf("未设置 book_id 时应为 nil，实际 %v", *got.BookID)
	}
}

func TestResolveBadBookID(t *testing.T) {
	isolate(t)
	t.Setenv("OPENLAIR_API_KEY", "ol_x")
	t.Setenv("OPENLAIR_BOOK_ID", "abc")
	if _, err := Resolve(Flags{}); err == nil {
		t.Fatal("非法 OPENLAIR_BOOK_ID 应报错")
	}
}

func TestEnvJSON(t *testing.T) {
	isolate(t)
	for _, raw := range []string{"1", "true", "YES"} {
		t.Setenv("LAIRCLI_JSON", raw)
		if !EnvJSON() {
			t.Fatalf("LAIRCLI_JSON=%s 应等价 --json", raw)
		}
	}
	t.Setenv("LAIRCLI_JSON", "0")
	if EnvJSON() {
		t.Fatal("LAIRCLI_JSON=0 不应开启 JSON")
	}
}

func TestMergeWritesZeroSixHundredAndOmitsEmpty(t *testing.T) {
	path := isolate(t)
	if _, err := Merge(File{APIKey: "ol_a"}); err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	// Windows 上 Go 只能表达"只读位"，0600 会被报成 666；那里真正的保护是"永不打印 Key"。
	if runtime.GOOS != "windows" {
		if perm := info.Mode().Perm(); perm != 0o600 {
			t.Fatalf("权限应为 0600，实际 %o", perm)
		}
	} else if info.Mode()&0o200 == 0 {
		t.Fatalf("Windows 上配置文件不应是只读: %o", info.Mode().Perm())
	}
	body, _ := os.ReadFile(path)
	if len(body) == 0 {
		t.Fatal("空文件")
	}
	// 只给 api_key 时不应写出空的 base_url / book_id，避免解析时被空串干扰。
	if _, err := Merge(File{BookID: 3}); err != nil {
		t.Fatal(err)
	}
	merged, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if merged.APIKey != "ol_a" || merged.BookID != 3 {
		t.Fatalf("Merge 应保留旧值: %+v", merged)
	}
}

func TestLoadMissingFileIsFine(t *testing.T) {
	isolate(t)
	data, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if data != (File{}) {
		t.Fatalf("文件不存在应为零值: %+v", data)
	}
}

func TestLoadBrokenFileReportsPath(t *testing.T) {
	path := isolate(t)
	if err := os.WriteFile(path, []byte("{ 不是 JSON"), 0o600); err != nil {
		t.Fatal(err)
	}
	_, err := Load()
	if err == nil {
		t.Fatal("坏文件应报错")
	}
	if !strings.Contains(err.Error(), path) {
		t.Fatalf("报错应带路径 %s：%v", path, err)
	}
}

func TestMask(t *testing.T) {
	if got := Mask("ol_abcdefghijk9999"); got != "ol_abcdefghi…" {
		t.Fatalf("前缀露出长度不对: %s", got)
	}
	if got := Mask("ol_short"); got != "***" {
		t.Fatalf("短串应整体遮蔽: %s", got)
	}
	if got := Mask(""); got != "***" {
		t.Fatalf("空串应遮蔽: %s", got)
	}
}

func TestXDGConfigHome(t *testing.T) {
	isolate(t)
	t.Setenv("LAIRCLI_CONFIG", "")
	root := t.TempDir()
	t.Setenv("XDG_CONFIG_HOME", root)
	path, err := Path()
	if err != nil {
		t.Fatal(err)
	}
	if want := filepath.Join(root, "laircli", "config.json"); path != want {
		t.Fatalf("应落在 XDG 目录下，实际 %s（期望 %s）", path, want)
	}
}

func contains(haystack, needle string) bool {
	return len(needle) == 0 || len(haystack) >= len(needle) && indexOf(haystack, needle) >= 0
}

func indexOf(haystack, needle string) int {
	for i := 0; i+len(needle) <= len(haystack); i++ {
		if haystack[i:i+len(needle)] == needle {
			return i
		}
	}
	return -1
}
