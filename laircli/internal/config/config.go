// Package config 管 ~/.laircli/config.json：API Key 落盘 + 三级解析（flag > env > 文件）。
//
// 安全约定：明文 Key 只进文件，任何输出与报错一律走 Mask()。Windows 的 chmod 只切只读位
// （ACL 不变），所以真正的保护是"永不打印"，不是文件权限。
package config

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// DefaultBaseURL 是生产站点；lair init 未指定 --base-url 时的默认值。
const DefaultBaseURL = "https://lair.lcc007.top"

// ErrNotConfigured 单独占退出码 3，与"接口调用失败"区分开。
var ErrNotConfigured = errors.New("尚未配置 API Key：先运行 lair init（或设置环境变量 OPENLAIR_API_KEY）")

// File 是配置文件内容；零值字段写出时省略（book_id 用 0 表示未设置，账本 id 从 1 起）。
type File struct {
	APIKey  string `json:"api_key,omitempty"`
	BaseURL string `json:"base_url,omitempty"`
	BookID  int    `json:"book_id,omitempty"`
	User    string `json:"user,omitempty"`
}

// Flags 是命令行全局 flag 传入的覆盖值；空串表示未给。
type Flags struct {
	APIKey  string
	BaseURL string
	JSON    bool
	Verbose bool
}

// Settings 是解析完成、可直接发请求的配置。
type Settings struct {
	APIKey  string
	BaseURL string
	BookID  *int
	JSON    bool
	Verbose bool
	User    string
}

// Path 返回配置文件路径；LAIRCLI_CONFIG 用于测试与多环境切换（取绝对路径）。
func Path() (string, error) {
	if override := strings.TrimSpace(os.Getenv("LAIRCLI_CONFIG")); override != "" {
		return override, nil
	}
	if xdg := strings.TrimSpace(os.Getenv("XDG_CONFIG_HOME")); xdg != "" {
		return filepath.Join(xdg, "laircli", "config.json"), nil
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("找不到用户主目录，无法定位配置文件：%w", err)
	}
	return filepath.Join(home, ".laircli", "config.json"), nil
}

// Load 读配置文件；文件不存在返回零值而不报错。
func Load() (File, error) {
	path, err := Path()
	if err != nil {
		return File{}, err
	}
	body, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		return File{}, nil
	}
	if err != nil {
		return File{}, fmt.Errorf("配置文件读取失败（%s）：%w", path, err)
	}
	var f File
	if err := json.Unmarshal(body, &f); err != nil {
		return File{}, fmt.Errorf("配置文件不可解析（%s）：%v", path, err)
	}
	return f, nil
}

// Merge 把非零字段合并进现有配置并落盘，返回写入路径。
func Merge(updates File) (string, error) {
	current, err := Load()
	if err != nil {
		return "", err
	}
	merged := current
	if updates.APIKey != "" {
		merged.APIKey = updates.APIKey
	}
	if updates.BaseURL != "" {
		merged.BaseURL = updates.BaseURL
	}
	if updates.BookID != 0 {
		merged.BookID = updates.BookID
	}
	if updates.User != "" {
		merged.User = updates.User
	}
	return Write(merged)
}

// Write 整体覆盖配置文件。
func Write(f File) (string, error) {
	path, err := Path()
	if err != nil {
		return "", err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return "", fmt.Errorf("无法创建配置目录：%w", err)
	}
	body, err := json.MarshalIndent(f, "", "  ")
	if err != nil {
		return "", err
	}
	if err := os.WriteFile(path, append(body, '\n'), 0o600); err != nil {
		return "", fmt.Errorf("配置文件写入失败（%s）：%w", path, err)
	}
	// os.WriteFile 只在新建时应用权限，已存在的 0644 文件不会被收紧。
	if err := os.Chmod(path, 0o600); err != nil {
		return "", fmt.Errorf("无法收紧配置文件权限（%s）：%w", path, err)
	}
	return path, nil
}

// EnvJSON 让 LAIRCLI_JSON=1 等价于全局 --json（flag 位置受限时更方便）。
func EnvJSON() bool {
	switch strings.ToLower(strings.TrimSpace(os.Getenv("LAIRCLI_JSON"))) {
	case "1", "true", "yes":
		return true
	}
	return false
}

// Mask 与后端 DTO 一致：只暴露前 12 字符（ol_ + 随机串前缀）。
func Mask(apiKey string) string {
	if len(apiKey) <= 12 {
		return "***"
	}
	return apiKey[:12] + "…"
}

// Resolve 按 flag > env > 文件 定出最终配置；缺 Key 直接返回 ErrNotConfigured。
func Resolve(flags Flags) (*Settings, error) {
	data, err := Load()
	if err != nil {
		return nil, err
	}
	key := first(flags.APIKey, os.Getenv("OPENLAIR_API_KEY"), data.APIKey)
	if key == "" {
		return nil, ErrNotConfigured
	}
	base := strings.TrimRight(first(flags.BaseURL, os.Getenv("OPENLAIR_BASE_URL"), data.BaseURL, DefaultBaseURL), "/")

	var bookID *int
	if env := strings.TrimSpace(os.Getenv("OPENLAIR_BOOK_ID")); env != "" {
		parsed, err := strconv.Atoi(env)
		if err != nil {
			return nil, fmt.Errorf("OPENLAIR_BOOK_ID 需为整数，当前为 %q", env)
		}
		bookID = &parsed
	} else if data.BookID != 0 {
		parsed := data.BookID
		bookID = &parsed
	}

	return &Settings{
		APIKey:  key,
		BaseURL: base,
		BookID:  bookID,
		JSON:    flags.JSON || EnvJSON(),
		Verbose: flags.Verbose,
		User:    data.User,
	}, nil
}

func first(values ...string) string {
	for _, v := range values {
		if trimmed := strings.TrimSpace(v); trimmed != "" {
			return trimmed
		}
	}
	return ""
}
