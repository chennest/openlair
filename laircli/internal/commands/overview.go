package commands

import (
	"fmt"
	"strings"

	"laircli/internal/cli"
	"laircli/internal/parse"
)

func overviewCmd() *cli.Command {
	return &cli.Command{
		Name:  "overview",
		Short: "总览看板（本月支出 / 待办 / 即将开始 / 习惯）",
		Run:   runOverview,
	}
}

func runOverview(ctx *cli.Context, in *cli.Inv) error {
	app := ctx.App.(*App)
	client, err := app.apiClient()
	if err != nil {
		return err
	}
	resp, err := client.Get("/api/overview", nil)
	if err != nil {
		return err
	}
	if app.isJSON() {
		return app.R.Data(resp.Data)
	}
	var data overviewDTO
	if err := resp.Into(&data); err != nil {
		return err
	}

	month := data.MonthExpense
	arrow := "→"
	if month.Trend > 0 {
		arrow = "↑"
	} else if month.Trend < 0 {
		arrow = "↓"
	}
	trend := month.Trend
	if trend < 0 {
		trend = -trend
	}
	used := ""
	if month.Budget != 0 {
		used = fmt.Sprintf(" （预算 %s，已用 %.0f%%）", parse.MoneyNoCents(month.Budget), month.Amount/month.Budget*100)
	}
	app.R.Log(fmt.Sprintf("本月支出 %s %s%.1f%%%s", parse.Money(month.Amount), arrow, trend, used))
	app.R.Log("")

	log := app.R.Log
	section(log, "待办", data.Todos, func(x overviewItemDTO) string {
		return strings.TrimRight(x.Text+"  "+x.Time+" · "+x.Tag, " ·")
	})
	section(log, "即将开始", data.Upcoming, func(x overviewItemDTO) string {
		return strings.TrimRight(x.Text+"  "+x.Date, " ")
	})
	section(log, "习惯", habitItems(data.Habits), func(x overviewItemDTO) string {
		return tick(x.Done) + " " + x.Name
	})
	return nil
}

// section 输出一段小标题 + 条目；空段落打「（无）」。
func section(println func(string), title string, items []overviewItemDTO, line func(overviewItemDTO) string) {
	println(title)
	if len(items) == 0 {
		println("  （无）")
	}
	for _, item := range items {
		println("  " + line(item))
	}
	println("")
}

// habitItems 把习惯条目映射进总览的统一结构，省掉再写一个 section 变体。
func habitItems(habits []habitDTO) []overviewItemDTO {
	items := make([]overviewItemDTO, 0, len(habits))
	for _, h := range habits {
		items = append(items, overviewItemDTO{Name: h.Name, Done: h.Done})
	}
	return items
}
