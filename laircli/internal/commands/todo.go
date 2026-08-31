package commands

import (
	"fmt"

	"laircli/internal/cli"
	"laircli/internal/parse"
	"laircli/internal/render"
)

func todoCmd() *cli.Command {
	return &cli.Command{
		Name:  "todo",
		Short: "待办",
		Sub:   []*cli.Command{todoList(), todoAdd(), todoDone(), todoUndo(), todoEdit(), todoRemove()},
	}
}

func todoList() *cli.Command {
	return &cli.Command{
		Name:  "list",
		Short: "待办清单",
		Flags: []*cli.Flag{
			{Name: "open", Short: "o", Usage: "只看未完成", Kind: cli.Bool},
		},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			items, err := fetchTodos(app)
			if err != nil {
				return err
			}
			if in.Bool("open") {
				var kept []todoDTO
				for _, t := range items {
					if !t.Done {
						kept = append(kept, t)
					}
				}
				items = kept
			}
			if app.isJSON() {
				return app.R.JSON(items)
			}
			rows := make([][]string, 0, len(items))
			for _, t := range items {
				rows = append(rows, []string{itoa(t.ID), tick(t.Done), t.Text, t.Quadrant, t.Due})
			}
			app.R.Table([]render.Col{
				{Title: "ID", Align: render.Right}, {Title: "状态", Align: render.Center},
				{Title: "内容"}, {Title: "象限"}, {Title: "期限"},
			}, rows)
			return nil
		},
	}
}

func todoAdd() *cli.Command {
	return &cli.Command{
		Name:  "add",
		Short: "新增待办",
		Args:  []cli.Arg{{Name: "内容"}},
		Flags: []*cli.Flag{
			{Name: "quadrant", Short: "q", Usage: "1-4 或 重要紧急 等象限名", Kind: cli.String},
			{Name: "due", Short: "d", Usage: "期限自由文本，如 今天/明天/本周", Kind: cli.String},
		},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			body := map[string]any{"text": in.Arg(0)}
			if in.Str("quadrant") != "" {
				quadrant, err := parse.Quadrant(in.Str("quadrant"))
				if err != nil {
					return err
				}
				body["quadrant"] = quadrant
			}
			if in.Str("due") != "" {
				body["due"] = in.Str("due")
			}
			resp, err := client.Post("/api/todo", body)
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var created mutation[todoDTO]
			if err := resp.Into(&created); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已添加：%s（%s · %s）", created.ID, created.Item.Text, created.Item.Quadrant, orDash(created.Item.Due)))
			return nil
		},
	}
}

func todoDone() *cli.Command { return todoSetDone("done", "标记完成", true) }
func todoUndo() *cli.Command { return todoSetDone("undo", "标记未完成", false) }

func todoSetDone(name, short string, done bool) *cli.Command {
	return &cli.Command{
		Name:  name,
		Short: short,
		Args:  []cli.Arg{{Name: "待办id"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			id, err := parseID(in.Arg(0), "待办 id")
			if err != nil {
				return err
			}
			if _, err := client.Put(fmt.Sprintf("/api/todo/%d", id), map[string]any{"done": done}); err != nil {
				return err
			}
			if done {
				app.R.OK(fmt.Sprintf("#%d 已完成", id))
				return nil
			}
			app.R.OK(fmt.Sprintf("#%d 已恢复为未完成", id))
			return nil
		},
	}
}

func todoEdit() *cli.Command {
	return &cli.Command{
		Name:  "edit",
		Short: "修改待办",
		Args:  []cli.Arg{{Name: "待办id"}},
		Flags: []*cli.Flag{
			{Name: "text", Usage: "新内容", Kind: cli.String},
			{Name: "quadrant", Short: "q", Usage: "1-4 或 象限名", Kind: cli.String},
			{Name: "due", Short: "d", Usage: "期限", Kind: cli.String},
		},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			body := map[string]any{}
			if in.Str("text") != "" {
				body["text"] = in.Str("text")
			}
			if in.Str("due") != "" {
				body["due"] = in.Str("due")
			}
			if in.Str("quadrant") != "" {
				quadrant, err := parse.Quadrant(in.Str("quadrant"))
				if err != nil {
					return err
				}
				body["quadrant"] = quadrant
			}
			if len(body) == 0 {
				return cli.Usagef("至少要给一个修改项（--text/--quadrant/--due）")
			}
			id, err := parseID(in.Arg(0), "待办 id")
			if err != nil {
				return err
			}
			if _, err := client.Put(fmt.Sprintf("/api/todo/%d", id), body); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已更新", id))
			return nil
		},
	}
}

func todoRemove() *cli.Command {
	return &cli.Command{
		Name:  "rm",
		Short: "删除待办",
		Args:  []cli.Arg{{Name: "待办id"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			id, err := parseID(in.Arg(0), "待办 id")
			if err != nil {
				return err
			}
			if _, err := client.Delete(fmt.Sprintf("/api/todo/%d", id)); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已删除", id))
			return nil
		},
	}
}

func fetchTodos(app *App) ([]todoDTO, error) {
	client, err := app.apiClient()
	if err != nil {
		return nil, err
	}
	resp, err := client.Get("/api/todo", nil)
	if err != nil {
		return nil, err
	}
	var data struct {
		Todos []todoDTO `json:"todos"`
	}
	if err := resp.Into(&data); err != nil {
		return nil, err
	}
	return data.Todos, nil
}

func tick(done bool) string {
	if done {
		return "✓"
	}
	return "·"
}

func orDash(value string) string {
	if value == "" {
		return "-"
	}
	return value
}
