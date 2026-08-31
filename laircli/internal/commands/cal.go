package commands

import (
	"fmt"
	"sort"

	"laircli/internal/cli"
	"laircli/internal/parse"
	"laircli/internal/render"
)

func calCmd() *cli.Command {
	return &cli.Command{
		Name:  "cal",
		Short: "日程",
		Sub:   []*cli.Command{calList(), calAdd(), calDone(), calUndo(), calRemove()},
	}
}

// fetchEvents 拉全量日程并按日期+时间排序：服务端不分页，区间筛选只能在客户端做。
func fetchEvents(app *App) ([]eventDTO, error) {
	client, err := app.apiClient()
	if err != nil {
		return nil, err
	}
	resp, err := client.Get("/api/calendar", nil)
	if err != nil {
		return nil, err
	}
	var data struct {
		Events []eventDTO `json:"events"`
	}
	if err := resp.Into(&data); err != nil {
		return nil, err
	}
	sort.SliceStable(data.Events, func(i, j int) bool {
		if data.Events[i].Date != data.Events[j].Date {
			return data.Events[i].Date < data.Events[j].Date
		}
		return data.Events[i].Time < data.Events[j].Time
	})
	return data.Events, nil
}

func calList() *cli.Command {
	return &cli.Command{
		Name:  "list",
		Short: "日程清单",
		Flags: []*cli.Flag{
			{Name: "day", Usage: "只看某天 YYYY-MM-DD / 今天", Kind: cli.String},
			{Name: "from", Usage: "起始日期", Kind: cli.String},
			{Name: "to", Usage: "结束日期", Kind: cli.String},
			{Name: "open", Short: "o", Usage: "只看未完成", Kind: cli.Bool},
		},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			events, err := fetchEvents(app)
			if err != nil {
				return err
			}
			if day := in.Str("day"); day != "" {
				target, err := parse.Date(day, "--day")
				if err != nil {
					return err
				}
				var kept []eventDTO
				for _, e := range events {
					if e.Date == target {
						kept = append(kept, e)
					}
				}
				events = kept
			} else {
				if from := in.Str("from"); from != "" {
					low, err := parse.Date(from, "--from")
					if err != nil {
						return err
					}
					var kept []eventDTO
					for _, e := range events {
						if e.Date >= low {
							kept = append(kept, e)
						}
					}
					events = kept
				}
				if to := in.Str("to"); to != "" {
					high, err := parse.Date(to, "--to")
					if err != nil {
						return err
					}
					var kept []eventDTO
					for _, e := range events {
						if e.Date <= high {
							kept = append(kept, e)
						}
					}
					events = kept
				}
			}
			if in.Bool("open") {
				var kept []eventDTO
				for _, e := range events {
					if !e.Done {
						kept = append(kept, e)
					}
				}
				events = kept
			}
			if app.isJSON() {
				return app.R.JSON(events)
			}
			rows := make([][]string, 0, len(events))
			for _, e := range events {
				rows = append(rows, []string{itoa(e.ID), e.Date, orDash(e.Time), e.Title, orDash(e.Location), tick(e.Done)})
			}
			app.R.Table([]render.Col{
				{Title: "ID", Align: render.Right}, {Title: "日期"}, {Title: "时间"},
				{Title: "标题"}, {Title: "地点"}, {Title: "状态", Align: render.Center},
			}, rows)
			return nil
		},
	}
}

func calAdd() *cli.Command {
	return &cli.Command{
		Name:  "add",
		Short: "新增日程",
		Args:  []cli.Arg{{Name: "标题"}},
		Flags: []*cli.Flag{
			{Name: "date", Short: "d", Usage: "YYYY-MM-DD / 今天 / 明天", Kind: cli.String},
			{Name: "time", Short: "T", Usage: "如 09:30（服务端默认 10:00）", Kind: cli.String},
			{Name: "location", Short: "l", Usage: "地点", Kind: cli.String},
		},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			body := map[string]any{"title": in.Arg(0)}
			if in.Str("date") != "" {
				day, err := parse.Date(in.Str("date"), "--date")
				if err != nil {
					return err
				}
				body["date"] = day
			}
			if in.Str("time") != "" {
				body["time"] = in.Str("time")
			}
			if in.Str("location") != "" {
				body["location"] = in.Str("location")
			}
			resp, err := client.Post("/api/calendar", body)
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var created mutation[eventDTO]
			if err := resp.Into(&created); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已安排：%s %s %s", created.ID, created.Item.Date, created.Item.Time, created.Item.Title))
			return nil
		},
	}
}

func calDone() *cli.Command { return calSetDone("done", "标记完成", true) }
func calUndo() *cli.Command { return calSetDone("undo", "标记未完成", false) }

func calSetDone(name, short string, done bool) *cli.Command {
	return &cli.Command{
		Name:  name,
		Short: short,
		Args:  []cli.Arg{{Name: "日程id"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			id, err := parseID(in.Arg(0), "日程 id")
			if err != nil {
				return err
			}
			if _, err := client.Put(fmt.Sprintf("/api/calendar/%d", id), map[string]any{"done": done}); err != nil {
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

func calRemove() *cli.Command {
	return &cli.Command{
		Name:  "rm",
		Short: "删除日程",
		Args:  []cli.Arg{{Name: "日程id"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			id, err := parseID(in.Arg(0), "日程 id")
			if err != nil {
				return err
			}
			if _, err := client.Delete(fmt.Sprintf("/api/calendar/%d", id)); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已删除", id))
			return nil
		},
	}
}
