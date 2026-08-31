// Command lair 是 OpenLair 的命令行客户端：凭 X-API-Key 访问后端 /api。
//
// 单二进制、零运行时依赖；命令面只做「读 + 高频写」，凭证签发与不可逆删除留在 Web 管理台。
package main

import (
	"os"

	"golang.org/x/term"

	"laircli/internal/cli"
	"laircli/internal/commands"
)

func main() {
	// 管道/重定向时不染颜色，避免把 ANSI 转义混进 jq 的输入。
	color := prepareConsole() && term.IsTerminal(int(os.Stdout.Fd())) && os.Getenv("NO_COLOR") == ""
	os.Exit(commands.Run(os.Args[1:], &cli.Context{Out: os.Stdout, Err: os.Stderr, In: os.Stdin}, color))
}
