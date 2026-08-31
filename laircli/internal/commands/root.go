package commands

import (
	"laircli/internal/cli"
	"laircli/internal/config"
	"laircli/internal/render"
)

// Root 拼装命令树。全局选项挂在根命令上，因此可以在任意位置出现。
func Root() *cli.Command {
	return &cli.Command{
		Name:  "lair",
		Short: "OpenLair 命令行客户端：凭 API Key 访问后端 /api",
		Long: "OpenLair 命令行客户端：凭 API Key 访问后端 /api，覆盖记账 / 待办 / 日程 / 笔记 / 习惯。\n" +
			"命令面刻意只做「读 + 高频写」：账本成员管理、删除账本、邀请码重置、API Key 签发与撤销\n" +
			"这类低频或高危操作留在 Web 端，命令行不做（详见 docs/cli/cli-guide.md）。",
		Flags: []*cli.Flag{
			{Name: "json", Usage: "输出纯 JSON，便于管道给 jq", Kind: cli.Bool},
			{Name: "base-url", Usage: "覆盖后端地址（不落盘）", Kind: cli.String},
			{Name: "api-key", Usage: "覆盖 API Key（不落盘）", Kind: cli.String},
			{Name: "verbose", Short: "v", Usage: "把每个请求的概要走 stderr 打出来", Kind: cli.Bool},
		},
		Prepare: prepare,
		Sub: []*cli.Command{
			initCmd(),
			whoamiCmd(),
			configCmd(),
			overviewCmd(),
			ledgerCmd(),
			bookCmd(),
			todoCmd(),
			calCmd(),
			noteCmd(),
			habitCmd(),
		},
	}
}

func prepare(ctx *cli.Context, in *cli.Inv) error {
	app := ctx.App.(*App)
	app.json = in.Bool("json")
	app.verbose = in.Bool("verbose")
	app.apiKey = in.Str("api-key")
	app.baseURL = in.Str("base-url")
	app.R = render.New(ctx.Out, ctx.Err, app.json || config.EnvJSON(), app.color)
	return nil
}
