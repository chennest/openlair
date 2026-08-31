package commands

import (
	"fmt"
	"strconv"
	"strings"

	"laircli/internal/cli"
	"laircli/internal/config"
	"laircli/internal/render"
)

func bookCmd() *cli.Command {
	return &cli.Command{
		Name:  "book",
		Short: "账本：列表 / 切换默认 / 创建 / 加入",
		Long: "账本：列表 / 切换默认 / 创建 / 用邀请码加入。\n" +
			"删除账本、清空数据、成员管理与邀请码重置都不在命令行做——去 Web 管理台，那些操作不可逆或会影响他人。",
		Sub: []*cli.Command{bookList(), bookCreate(), bookUse(), bookCurrent(), bookJoin()},
	}
}

func bookList() *cli.Command {
	return &cli.Command{
		Name:  "list",
		Short: "我参与的账本",
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			resp, err := client.Get("/api/books", nil)
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var books []bookDTO
			if err := resp.Into(&books); err != nil {
				return err
			}
			rows := make([][]string, 0, len(books))
			for _, b := range books {
				rows = append(rows, []string{itoa(b.ID), b.Name, bookTypeLabel(b.Type), memberNames(b.Members)})
			}
			app.R.Table([]render.Col{{Title: "ID", Align: render.Right}, {Title: "名称"}, {Title: "类型"}, {Title: "成员"}}, rows)
			app.R.Hint("设默认账本：lair book use <id>")
			return nil
		},
	}
}

func bookCreate() *cli.Command {
	return &cli.Command{
		Name:  "create",
		Short: "新建账本（建的人自动成为 owner）",
		Args:  []cli.Arg{{Name: "名称"}},
		Flags: []*cli.Flag{
			{Name: "type", Short: "t", Usage: "personal / shared（默认 personal）", Kind: cli.String, Default: "personal"},
		},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			kind := in.Str("type")
			if kind != "personal" && kind != "shared" {
				return cli.Usagef("账本类型只能是 personal 或 shared，当前为 %q", kind)
			}
			resp, err := client.Post("/api/books", map[string]any{"name": in.Arg(0), "type": kind})
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var created struct {
				Book bookDTO `json:"book"`
			}
			if err := resp.Into(&created); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("账本 #%d %s 已创建", created.Book.ID, created.Book.Name))
			app.R.Hint(fmt.Sprintf("设为默认：lair book use %d", created.Book.ID))
			return nil
		},
	}
}

func bookUse() *cli.Command {
	return &cli.Command{
		Name:  "use",
		Short: "把某个账本设为默认（写入配置文件）",
		Args:  []cli.Arg{{Name: "账本id"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			want, err := strconv.Atoi(in.Arg(0))
			if err != nil {
				return cli.Usagef("账本 id 需为整数，当前为 %q", in.Arg(0))
			}
			resp, err := client.Get("/api/books", nil)
			if err != nil {
				return err
			}
			var books []bookDTO
			if err := resp.Into(&books); err != nil {
				return err
			}
			for _, b := range books {
				if b.ID != want {
					continue
				}
				if _, err := config.Merge(config.File{BookID: want}); err != nil {
					return err
				}
				app.R.OK(fmt.Sprintf("默认账本已切换为 #%d %s", want, b.Name))
				return nil
			}
			return fmt.Errorf("账本 %d 不存在或你已不在其中：lair book list 看可选", want)
		},
	}
}

func bookCurrent() *cli.Command {
	return &cli.Command{
		Name:  "current",
		Short: "显示当前生效的账本及来源",
		Flags: []*cli.Flag{bookFlag()},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			book, explicit, err := app.resolveBook(client, in.OptInt("book"))
			if err != nil {
				return err
			}
			source := "自动取首个个人账本"
			if explicit {
				source = "命令行 --book / 配置默认"
			}
			if app.isJSON() {
				return app.R.JSON(map[string]any{"id": book.ID, "name": book.Name, "type": book.Type, "source": source})
			}
			app.R.Log(fmt.Sprintf("当前账本：#%d %s（%s）· 来源：%s", book.ID, book.Name, bookTypeLabel(book.Type), source))
			return nil
		},
	}
}

func bookJoin() *cli.Command {
	return &cli.Command{
		Name:  "join",
		Short: "用邀请码加入共享账本（成为 editor）",
		Args:  []cli.Arg{{Name: "邀请码"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			code := strings.TrimSpace(in.Arg(0))
			if code == "" {
				return cli.Usagef("邀请码不能为空")
			}
			resp, err := client.Post("/api/books/join", map[string]any{"code": code})
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var joined struct {
				Book bookDTO `json:"book"`
			}
			if err := resp.Into(&joined); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("已加入账本 #%d %s", joined.Book.ID, joined.Book.Name))
			app.R.Hint(fmt.Sprintf("设为默认：lair book use %d", joined.Book.ID))
			return nil
		},
	}
}

func memberNames(members []memberDTO) string {
	names := make([]string, 0, len(members))
	for _, m := range members {
		name := m.User.Name
		if name == "" {
			name = "?"
		}
		names = append(names, name)
	}
	if len(names) == 0 {
		return "-"
	}
	return strings.Join(names, "、")
}
