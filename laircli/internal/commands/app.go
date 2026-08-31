// Package commands 是 lair 的命令面：每个业务模块一个文件，只做"参数 → 接口调用 → 渲染"。
package commands

import (
	"errors"

	"laircli/internal/api"
	"laircli/internal/cli"
	"laircli/internal/config"
	"laircli/internal/render"
)

// App 是一次进程的运行期对象：全局选项 + 惰性的配置与客户端。
type App struct {
	ctx     *cli.Context
	color   bool
	json    bool
	verbose bool
	apiKey  string
	baseURL string

	R        *render.R
	settings *config.Settings
	client   *api.Client
}

// client 拿到可用的 API 客户端；缺 API Key 时返回 config.ErrNotConfigured（退出码 3）。
func (a *App) apiClient() (*api.Client, error) {
	if a.client != nil {
		return a.client, nil
	}
	settings, err := config.Resolve(config.Flags{APIKey: a.apiKey, BaseURL: a.baseURL, JSON: a.json, Verbose: a.verbose})
	if err != nil {
		return nil, err
	}
	a.settings = settings
	client := api.New(settings)
	if settings.Verbose {
		client.Debug = a.R.Debug
	}
	a.client = client
	return client, nil
}

// isJSON 决定 stdout 是否只留纯 JSON（--json 或 LAIRCLI_JSON=1）。
func (a *App) isJSON() bool { return a.json || config.EnvJSON() }

// defaultBookID 是配置文件/环境变量里的默认账本，未设置为 nil。
func (a *App) defaultBookID() *int {
	if a.settings == nil {
		return nil
	}
	return a.settings.BookID
}

// Run 是真实入口：解析 → 执行 → 把错误翻译成退出码与文案。
//
// 退出码：0 成功，1 接口/业务失败，2 用法错误，3 未配置。
func Run(args []string, ctx *cli.Context, color bool) int {
	app := &App{ctx: ctx, color: color}
	app.R = render.New(ctx.Out, ctx.Err, false, color)
	ctx.App = app

	err := cli.Execute(Root(), args, ctx)
	if err == nil {
		return 0
	}
	code := 1
	var usage *cli.UsageError
	switch {
	case errors.As(err, &usage):
		code = 2
	case errors.Is(err, config.ErrNotConfigured):
		code = 3
	}
	app.R.Fail(err.Error())
	if code == 2 {
		app.R.Hint("用 --help 看用法")
	}
	return code
}
