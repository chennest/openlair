package commands

import (
	"fmt"
	"strings"

	"laircli/internal/cli"
	"laircli/internal/render"
)

func noteCmd() *cli.Command {
	return &cli.Command{
		Name:  "note",
		Short: "笔记",
		Sub:   []*cli.Command{noteList(), noteShow(), noteAdd(), noteRemove()},
	}
}

// fetchNotes 拉最近笔记；后端没有按 id 取单篇的接口，show 只能在列表里挑。
func fetchNotes(app *App) ([]noteDTO, error) {
	client, err := app.apiClient()
	if err != nil {
		return nil, err
	}
	resp, err := client.Get("/api/notes", nil)
	if err != nil {
		return nil, err
	}
	var data struct {
		Notes []noteDTO `json:"notes"`
	}
	if err := resp.Into(&data); err != nil {
		return nil, err
	}
	return data.Notes, nil
}

func noteList() *cli.Command {
	return &cli.Command{
		Name:  "list",
		Short: "最近笔记（按更新时间倒序）",
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			notes, err := fetchNotes(app)
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.JSON(notes)
			}
			rows := make([][]string, 0, len(notes))
			for _, n := range notes {
				summary := n.Summary
				if len(summary) > 40 {
					summary = truncate(summary, 40)
				}
				rows = append(rows, []string{itoa(n.ID), n.Title, strings.Join(n.Tags, " "), summary, n.UpdatedAt})
			}
			app.R.Table([]render.Col{
				{Title: "ID", Align: render.Right}, {Title: "标题"}, {Title: "标签"}, {Title: "摘要"}, {Title: "更新于"},
			}, rows)
			return nil
		},
	}
}

func noteShow() *cli.Command {
	return &cli.Command{
		Name:  "show",
		Short: "看一篇笔记的完整正文",
		Args:  []cli.Arg{{Name: "笔记id"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			id, err := parseID(in.Arg(0), "笔记 id")
			if err != nil {
				return err
			}
			notes, err := fetchNotes(app)
			if err != nil {
				return err
			}
			for _, n := range notes {
				if n.ID != id {
					continue
				}
				if app.isJSON() {
					return app.R.JSON(n)
				}
				tags := strings.Join(n.Tags, " ")
				if tags != "" {
					tags = "#" + tags
				}
				app.R.Log(strings.TrimRight(n.Title+"  "+tags, " "))
				app.R.Log("更新于 " + orDash(n.UpdatedAt))
				app.R.Log("")
				app.R.Log(orDash(n.Summary))
				return nil
			}
			return fmt.Errorf("笔记 %d 不存在：lair note list 看可选", id)
		},
	}
}

func noteAdd() *cli.Command {
	return &cli.Command{
		Name:  "add",
		Short: "快速记一篇笔记",
		Long: "快速记一篇笔记：位置参数是正文（可多词，空格拼接），也可用 --body 传整段。\n" +
			"示例：lair note add 记一下今天的需求 --title 周会 --tag 工作",
		Args: []cli.Arg{{Name: "正文", Optional: true, Variadic: true}},
		Flags: []*cli.Flag{
			{Name: "title", Usage: "标题（默认「未命名」）", Kind: cli.String},
			{Name: "body", Usage: "正文（与位置参数二选一）", Kind: cli.String},
			{Name: "tag", Usage: "标签，可重复", Kind: cli.Strings},
		},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			content := in.Str("body")
			if content == "" {
				content = strings.TrimSpace(strings.Join(in.Rest(0), " "))
			}
			if content == "" {
				return cli.Usagef("正文不能为空")
			}
			body := map[string]any{"summary": content}
			if in.Str("title") != "" {
				body["title"] = in.Str("title")
			}
			if tags := in.List("tag"); len(tags) > 0 {
				body["tags"] = tags
			}
			resp, err := client.Post("/api/notes", body)
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var created mutation[noteDTO]
			if err := resp.Into(&created); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已记录：%s", created.ID, created.Item.Title))
			return nil
		},
	}
}

func noteRemove() *cli.Command {
	return &cli.Command{
		Name:  "rm",
		Short: "删除笔记",
		Args:  []cli.Arg{{Name: "笔记id"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			id, err := parseID(in.Arg(0), "笔记 id")
			if err != nil {
				return err
			}
			if _, err := client.Delete(fmt.Sprintf("/api/notes/%d", id)); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已删除", id))
			return nil
		},
	}
}

// truncate 按显示宽度截断，避免把中文词切半个字。
func truncate(value string, limit int) string {
	total := 0
	for i, r := range value {
		total += render.Width(string(r))
		if total > limit {
			return strings.TrimRight(value[:i], " ") + "…"
		}
	}
	return value
}
