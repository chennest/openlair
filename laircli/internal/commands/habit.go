package commands

import (
	"fmt"

	"laircli/internal/cli"
	"laircli/internal/render"
)

func habitCmd() *cli.Command {
	return &cli.Command{
		Name:  "habit",
		Short: "习惯打卡",
		Sub:   []*cli.Command{habitList(), habitAdd(), habitCheck(), habitUncheck(), habitRemove()},
	}
}

func habitList() *cli.Command {
	return &cli.Command{
		Name:  "list",
		Short: "习惯与本周打卡",
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			items, err := fetchHabits(app)
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.JSON(items)
			}
			rows := make([][]string, 0, len(items))
			for _, h := range items {
				rows = append(rows, []string{itoa(h.ID), h.Name, tick(h.Done), fmt.Sprintf("%d 天", h.Streak), weekBar(h.Week)})
			}
			app.R.Table([]render.Col{
				{Title: "ID", Align: render.Right}, {Title: "习惯"}, {Title: "今日", Align: render.Center},
				{Title: "连续", Align: render.Right}, {Title: "本周"},
			}, rows)
			return nil
		},
	}
}

func habitAdd() *cli.Command {
	return &cli.Command{
		Name:  "add",
		Short: "新建习惯",
		Args:  []cli.Arg{{Name: "习惯名"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			resp, err := client.Post("/api/habits", map[string]any{"name": in.Arg(0)})
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var created mutation[habitDTO]
			if err := resp.Into(&created); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已新建习惯：%s", created.ID, created.Item.Name))
			return nil
		},
	}
}

func habitCheck() *cli.Command {
	return &cli.Command{
		Name:  "check",
		Short: "今日打卡",
		Args:  []cli.Arg{{Name: "习惯id"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			id, err := parseID(in.Arg(0), "习惯 id")
			if err != nil {
				return err
			}
			resp, err := client.Put(fmt.Sprintf("/api/habits/%d", id), map[string]any{"done": true})
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var updated mutation[habitDTO]
			if err := resp.Into(&updated); err != nil {
				return err
			}
			// 后端 update 不重算 week 数组，所以这里只报连续天数，不画本周格子。
			app.R.OK(fmt.Sprintf("%s 今日已打卡（当前连续 %d 天）", updated.Item.Name, updated.Item.Streak))
			return nil
		},
	}
}

func habitUncheck() *cli.Command {
	return &cli.Command{
		Name:  "uncheck",
		Short: "取消今日打卡",
		Args:  []cli.Arg{{Name: "习惯id"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			id, err := parseID(in.Arg(0), "习惯 id")
			if err != nil {
				return err
			}
			if _, err := client.Put(fmt.Sprintf("/api/habits/%d", id), map[string]any{"done": false}); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已取消今日打卡", id))
			return nil
		},
	}
}

func habitRemove() *cli.Command {
	return &cli.Command{
		Name:  "rm",
		Short: "删除习惯",
		Args:  []cli.Arg{{Name: "习惯id"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			id, err := parseID(in.Arg(0), "习惯 id")
			if err != nil {
				return err
			}
			if _, err := client.Delete(fmt.Sprintf("/api/habits/%d", id)); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已删除", id))
			return nil
		},
	}
}

func fetchHabits(app *App) ([]habitDTO, error) {
	client, err := app.apiClient()
	if err != nil {
		return nil, err
	}
	resp, err := client.Get("/api/habits", nil)
	if err != nil {
		return nil, err
	}
	var data struct {
		Habits []habitDTO `json:"habits"`
	}
	if err := resp.Into(&data); err != nil {
		return nil, err
	}
	return data.Habits, nil
}
