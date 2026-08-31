//go:build windows

package main

import (
	"syscall"
	"unsafe"
)

const (
	cpUTF8                          = 65001
	enableVirtualTerminalProcessing = 0x0004
)

var (
	kernel32               = syscall.NewLazyDLL("kernel32.dll")
	procSetConsoleCP       = kernel32.NewProc("SetConsoleCP")
	procSetConsoleOutputCP = kernel32.NewProc("SetConsoleOutputCP")
	procGetConsoleMode     = kernel32.NewProc("GetConsoleMode")
	procSetConsoleMode     = kernel32.NewProc("SetConsoleMode")
	procGetStdHandle       = kernel32.NewProc("GetStdHandle")
)

// prepareConsole 把控制台代码页切到 UTF-8，并尝试打开 ANSI 转义支持，返回"能不能安全输出颜色"。
//
// Python 版要靠 PYTHONUTF8=1 才能传中文参数，是因为 CPython 用本地代码页解码 argv；
// Go 的 argv 走 UTF-16 → UTF-8，本身就没这个问题，这里只剩"输出侧"的代码页要处理。
func prepareConsole() bool {
	procSetConsoleCP.Call(cpUTF8)
	procSetConsoleOutputCP.Call(cpUTF8)

	stdout, _, _ := procGetStdHandle.Call(uintptr(syscall.Stdout))
	var mode uint32
	if ret, _, _ := procGetConsoleMode.Call(stdout, uintptr(unsafe.Pointer(&mode))); ret == 0 {
		// 不是控制台（重定向到文件或管道）：代码页无意义，颜色由调用方按 IsTerminal 关掉。
		return true
	}
	if ret, _, _ := procSetConsoleMode.Call(stdout, uintptr(mode|enableVirtualTerminalProcessing)); ret == 0 {
		return false
	}
	return true
}
