package commands

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"

	"golang.org/x/term"

	"laircli/internal/api"
	"laircli/internal/cli"
	"laircli/internal/config"
	"laircli/internal/render"
)

// 配置类命令：init / whoami / config。API Key 由 Web 端「API Key」页创建后手动粘贴，
// 命令行不签发、不撤销凭证——所以这里没有 keys 子命令。

func initCmd() *cli.Command {
	return &cli.Command{
		Name:  "init",
		Short: "把 API Key 写到配置文件（校验通过才落盘）",
		Long: "把 API Key 写到 ~/.laircli/config.json（Windows 同路径，权限 0600）。\n" +
			"Key 在 Web 管理台「API Key」页创建，明文只显示一次；命令行拿不到就重新生成一把。\n" +
			"非交互：lair --api-key ol_xxx --base-url http://127.0.0.1:8001 init",
		Run: runInit,
	}
}

func runInit(ctx *cli.Context, in *cli.Inv) error {
	app := ctx.App.(*App)
	p := &prompter{ctx: ctx, reader: bufio.NewReader(ctx.In)}

	key := strings.TrimSpace(app.apiKey)
	if key == "" {
		typed, err := p.secret("粘贴 API Key（ol_ 开头，输入不回显）")
		if err != nil {
			return err
		}
		key = strings.TrimSpace(typed)
	}
	if !strings.HasPrefix(key, "ol_") {
		return fmt.Errorf("这看起来不是 API Key：应以 ol_ 开头（约 46 字符）")
	}

	base := strings.TrimRight(strings.TrimSpace(app.baseURL), "/")
	if base == "" {
		existing, err := config.Load()
		if err != nil {
			return err
		}
		def := config.DefaultBaseURL
		if existing.BaseURL != "" {
			def = existing.BaseURL
		}
		typed, err := p.line("后端地址", def)
		if err != nil {
			return err
		}
		base = strings.TrimRight(typed, "/")
	}

	probe := api.New(&config.Settings{APIKey: key, BaseURL: base})
	resp, err := probe.Get("/api/auth/me", nil)
	if err != nil {
		app.R.Fail("Key 校验失败，未写入任何文件")
		return err
	}
	var me meDTO
	if err := resp.Into(&me); err != nil {
		return err
	}
	path, err := config.Merge(config.File{APIKey: key, BaseURL: base, User: me.Name})
	if err != nil {
		return err
	}
	app.R.Hint("配置已写入 " + path)
	app.R.OK(fmt.Sprintf("已连接 %s —— 你好，%s（%s）", base, me.Name, orDash(me.Email)))
	app.R.Hint("下一步：lair book list 看一下账本，再 lair book use <id> 设成默认账本")
	return nil
}

func whoamiCmd() *cli.Command {
	return &cli.Command{
		Name:  "whoami",
		Short: "当前 Key 属于哪个用户",
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			resp, err := client.Get("/api/auth/me", nil)
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var me meDTO
			if err := resp.Into(&me); err != nil {
				return err
			}
			app.R.Table([]render.Col{{Title: "字段"}, {Title: "值"}}, [][]string{
				{"id", itoa(me.ID)},
				{"昵称", me.Name},
				{"邮箱", orDash(me.Email)},
				{"注册于", orDash(me.CreatedAt)},
			})
			return nil
		},
	}
}

func configCmd() *cli.Command {
	return &cli.Command{
		Name:  "config",
		Short: "显示当前配置（Key 只展示前缀）",
		Run:   runConfigShow,
	}
}

func runConfigShow(ctx *cli.Context, in *cli.Inv) error {
	app := ctx.App.(*App)
	path, err := config.Path()
	if err != nil {
		return err
	}
	data, err := config.Load()
	if err != nil {
		return err
	}
	if app.isJSON() {
		return app.R.JSON(map[string]any{
			"path":     path,
			"api_key":  config.Mask(data.APIKey),
			"base_url": orDefault(data.BaseURL, config.DefaultBaseURL),
			"book_id":  data.BookID,
			"user":     data.User,
		})
	}
	exists := ""
	if _, statErr := os.Stat(path); errors.Is(statErr, os.ErrNotExist) {
		exists = "（尚未创建）"
	}
	apiKey := "（未配置）"
	if data.APIKey != "" {
		apiKey = config.Mask(data.APIKey)
	}
	bookID := "（未设置：ledger 会自动取首个个人账本）"
	if data.BookID != 0 {
		bookID = strconv.Itoa(data.BookID)
	}
	app.R.Table([]render.Col{{Title: "配置"}, {Title: "值"}}, [][]string{
		{"配置文件", path + exists},
		{"api_key", apiKey},
		{"base_url", orDefault(data.BaseURL, config.DefaultBaseURL)},
		{"book_id", bookID},
		{"user", orDash(data.User)},
	})
	app.R.Hint("换 Key 或地址：重新 lair init；换默认账本：lair book use <id>")
	return nil
}

// prompter 处理交互式输入：终端下 Key 不回显，管道里退化成普通行输入。
type prompter struct {
	ctx    *cli.Context
	reader *bufio.Reader
}

func (p *prompter) line(label, def string) (string, error) {
	suffix := "："
	if def != "" {
		suffix = fmt.Sprintf(" [%s]：", def)
	}
	fmt.Fprint(p.ctx.Err, label+suffix)
	text, err := p.reader.ReadString('\n')
	if err != nil && strings.TrimSpace(text) == "" {
		if errors.Is(err, io.EOF) {
			return def, nil
		}
		return "", fmt.Errorf("读取输入失败：%w", err)
	}
	value := strings.TrimSpace(text)
	if value == "" {
		return def, nil
	}
	return value, nil
}

func (p *prompter) secret(label string) (string, error) {
	fmt.Fprint(p.ctx.Err, label+"：")
	if term.IsTerminal(int(os.Stdin.Fd())) {
		raw, err := term.ReadPassword(int(os.Stdin.Fd()))
		fmt.Fprintln(p.ctx.Err)
		if err != nil {
			return "", fmt.Errorf("读取输入失败：%w", err)
		}
		return string(raw), nil
	}
	fmt.Fprintln(p.ctx.Err, "（非终端输入，内容会回显）")
	text, err := p.reader.ReadString('\n')
	if err != nil && strings.TrimSpace(text) == "" {
		return "", fmt.Errorf("读取输入失败：%w", err)
	}
	return strings.TrimSpace(text), nil
}

func orDefault(value, fallback string) string {
	if value == "" {
		return fallback
	}
	return value
}
