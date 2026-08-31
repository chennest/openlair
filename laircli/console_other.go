//go:build !windows

package main

// prepareConsole 在非 Windows 上没有代码页要处理；颜色开关交给 IsTerminal。
func prepareConsole() bool { return true }
