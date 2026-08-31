package commands

import (
	"fmt"
	"strconv"

	"laircli/internal/api"
	"laircli/internal/cli"
	"laircli/internal/parse"
	"laircli/internal/render"
)

func ledgerCmd() *cli.Command {
	return &cli.Command{
		Name:  "ledger",
		Short: "记账：流水 / 分类 / 趋势 / 预算",
		Sub: []*cli.Command{
			ledgerAdd(), ledgerList(), ledgerEdit(), ledgerRemove(),
			ledgerCategories(), ledgerTrend(), ledgerBudget(),
		},
	}
}

func bookFlag() *cli.Flag {
	return &cli.Flag{Name: "book", Short: "b", Usage: "账本 id（覆盖默认）", Kind: cli.Int}
}

func ledgerAdd() *cli.Command {
	return &cli.Command{
		Name:  "add",
		Short: "记一笔账",
		Args:  []cli.Arg{{Name: "金额"}},
		Flags: []*cli.Flag{
			{Name: "type", Short: "t", Usage: "expense/income 或 支出/收入（省略则按分类推断）", Kind: cli.String},
			{Name: "category", Short: "c", Usage: "分类名或 id", Kind: cli.String},
			{Name: "date", Short: "d", Usage: "YYYY-MM-DD / 今天 / 昨天 / 明天", Kind: cli.String},
			{Name: "note", Short: "n", Usage: "备注", Kind: cli.String},
			bookFlag(),
		},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			amount, err := strconv.ParseFloat(in.Arg(0), 64)
			if err != nil {
				return cli.Usagef("金额需为数字，当前为 %q", in.Arg(0))
			}
			var wantedType string
			if in.Str("type") != "" {
				if wantedType, err = parse.Type(in.Str("type")); err != nil {
					return err
				}
			}
			cats, err := app.categories(client, wantedType)
			if err != nil {
				return err
			}
			picked, err := pickCategory(cats, wantedType, in.Str("category"))
			if err != nil {
				return err
			}
			txType := wantedType
			switch {
			case txType == "" && picked != nil:
				txType = picked.Type
			case txType == "":
				txType = parse.Expense
			}
			book, explicit, err := app.resolveBook(client, in.OptInt("book"))
			if err != nil {
				return err
			}

			body := map[string]any{"type": txType, "amount": amount, "bookId": book.ID}
			if picked != nil {
				body["categoryId"] = picked.ID
			}
			if in.Str("date") != "" {
				day, err := parse.Date(in.Str("date"), "--date")
				if err != nil {
					return err
				}
				body["date"] = day
			}
			if in.Str("note") != "" {
				body["note"] = in.Str("note")
			}

			resp, err := client.Post("/api/ledger", body)
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var created mutation[transactionDTO]
			if err := resp.Into(&created); err != nil {
				return err
			}
			if line := bookLine(book, explicit); line != "" {
				app.R.Hint(line)
			}
			item := created.Item
			app.R.OK(fmt.Sprintf("#%d 已记 %s %s · %s · %s%s", created.ID, item.Type, parse.Money(item.Amount),
				item.Category, item.Date, noteSuffix(item.Note)))
			if picked == nil {
				app.R.Hint("未指定分类，服务端按「其他」入账（下次用 -c 餐饮）")
			}
			return nil
		},
	}
}

func ledgerList() *cli.Command {
	return &cli.Command{
		Name:  "list",
		Short: "查流水（含区间汇总与预算）",
		Flags: []*cli.Flag{
			{Name: "type", Short: "t", Usage: "expense/income 或 支出/收入", Kind: cli.String},
			{Name: "category", Short: "c", Usage: "分类名或 id", Kind: cli.String},
			{Name: "keyword", Short: "k", Usage: "匹配备注或分类名", Kind: cli.String},
			{Name: "start", Usage: "起始日期 YYYY-MM-DD / 今天", Kind: cli.String},
			{Name: "end", Usage: "结束日期 YYYY-MM-DD / 今天", Kind: cli.String},
			{Name: "page", Usage: "页码（默认 1）", Kind: cli.Int, Default: 1},
			{Name: "page-size", Usage: "每页条数（默认 20，上限 200）", Kind: cli.Int, Default: 20},
			bookFlag(),
		},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			var wantedType string
			if in.Str("type") != "" {
				if wantedType, err = parse.Type(in.Str("type")); err != nil {
					return err
				}
			}
			cats, err := app.categories(client, wantedType)
			if err != nil {
				return err
			}
			picked, err := pickCategory(cats, wantedType, in.Str("category"))
			if err != nil {
				return err
			}
			book, explicit, err := app.resolveBook(client, in.OptInt("book"))
			if err != nil {
				return err
			}
			start, end := in.Str("start"), in.Str("end")
			var startDate, endDate string
			if startDate, err = optionalDate(start, "--start"); err != nil {
				return err
			}
			if endDate, err = optionalDate(end, "--end"); err != nil {
				return err
			}
			page := int(in.Int("page"))
			if page < 1 {
				page = 1
			}
			pageSize := int(in.Int("page-size"))
			if pageSize < 1 {
				pageSize = 20
			}
			if pageSize > 200 {
				pageSize = 200
			}

			query := api.Query{
				"bookId": itoa(book.ID), "type": wantedType, "keyword": in.Str("keyword"),
				"startDate": startDate, "endDate": endDate,
				"page": itoa(page), "pageSize": itoa(pageSize),
			}
			if picked != nil {
				query["categoryId"] = itoa(picked.ID)
			}
			resp, err := client.Get("/api/ledger", query.Values())
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var data ledgerPageDTO
			if err := resp.Into(&data); err != nil {
				return err
			}
			if line := bookLine(book, explicit); line != "" {
				app.R.Hint(line)
			}
			rows := make([][]string, 0, len(data.Transactions))
			for _, t := range data.Transactions {
				rows = append(rows, []string{itoa(t.ID), t.Date, t.Type, t.Category, parse.Money(t.Amount), t.Note, t.UserName})
			}
			app.R.Table([]render.Col{
				{Title: "ID", Align: render.Right}, {Title: "日期"}, {Title: "类型"}, {Title: "分类"},
				{Title: "金额", Align: render.Right}, {Title: "备注"}, {Title: "记账人"},
			}, rows)
			app.R.Log(fmt.Sprintf("收入 %s ｜ 支出 %s ｜ 结余 %s ｜ 当月预算 %s ｜ 共 %d 条（第 %d 页，每页 %d）",
				parse.Money(data.Summary.Income), parse.Money(data.Summary.Expense), parse.Money(data.Summary.Balance),
				parse.MoneyOf(data.Budget), data.Total, data.Page, data.PageSize))
			return nil
		},
	}
}

func ledgerEdit() *cli.Command {
	return &cli.Command{
		Name:  "edit",
		Short: "改一笔流水（只提交显式给的字段；后端不支持清空）",
		Args:  []cli.Arg{{Name: "流水id"}},
		Flags: []*cli.Flag{
			{Name: "amount", Usage: "新金额", Kind: cli.Float},
			{Name: "type", Short: "t", Usage: "expense/income 或 支出/收入", Kind: cli.String},
			{Name: "category", Short: "c", Usage: "分类名或 id（需同时给 --type）", Kind: cli.String},
			{Name: "date", Short: "d", Usage: "YYYY-MM-DD / 今天 / 昨天 / 明天", Kind: cli.String},
			{Name: "note", Short: "n", Usage: "备注", Kind: cli.String},
		},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			body := map[string]any{}
			if in.Has("amount") {
				body["amount"] = in.Float("amount")
			}
			if in.Str("type") != "" {
				mapped, err := parse.Type(in.Str("type"))
				if err != nil {
					return err
				}
				body["type"] = mapped
			}
			if in.Str("date") != "" {
				day, err := parse.Date(in.Str("date"), "--date")
				if err != nil {
					return err
				}
				body["date"] = day
			}
			if in.Has("note") {
				body["note"] = in.Str("note")
			}
			if in.Str("category") != "" {
				if in.Str("type") == "" {
					return cli.Usagef("改分类需同时给 --type，避免分类与收支方向不一致")
				}
				cats, err := app.categories(client, body["type"].(string))
				if err != nil {
					return err
				}
				picked, err := pickCategory(cats, body["type"].(string), in.Str("category"))
				if err != nil {
					return err
				}
				if picked != nil {
					body["categoryId"] = picked.ID
				}
			}
			if len(body) == 0 {
				return cli.Usagef("至少要给一个修改项（--amount/--type/--category/--date/--note）")
			}
			txID, err := strconv.Atoi(in.Arg(0))
			if err != nil {
				return cli.Usagef("流水 id 需为整数，当前为 %q", in.Arg(0))
			}
			resp, err := client.Put(fmt.Sprintf("/api/ledger/%d", txID), body)
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var updated mutation[transactionDTO]
			if err := resp.Into(&updated); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已更新 → %s %s · %s", txID, updated.Item.Type,
				parse.Money(updated.Item.Amount), updated.Item.Category))
			return nil
		},
	}
}

func ledgerRemove() *cli.Command {
	return &cli.Command{
		Name:  "rm",
		Short: "删一笔流水",
		Args:  []cli.Arg{{Name: "流水id"}},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			txID, err := strconv.Atoi(in.Arg(0))
			if err != nil {
				return cli.Usagef("流水 id 需为整数，当前为 %q", in.Arg(0))
			}
			if _, err := client.Delete(fmt.Sprintf("/api/ledger/%d", txID)); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("#%d 已删除", txID))
			return nil
		},
	}
}

func ledgerCategories() *cli.Command {
	return &cli.Command{
		Name:  "categories",
		Short: "列出可用分类（全局固定 1-16）",
		Flags: []*cli.Flag{
			{Name: "type", Short: "t", Usage: "只看支出或收入侧", Kind: cli.String},
		},
		Run: func(ctx *cli.Context, in *cli.Inv) error {
			app := ctx.App.(*App)
			client, err := app.apiClient()
			if err != nil {
				return err
			}
			var wantedType string
			if in.Str("type") != "" {
				if wantedType, err = parse.Type(in.Str("type")); err != nil {
					return err
				}
			}
			resp, err := client.Get("/api/ledger/categories", api.Query{"type": wantedType}.Values())
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var cats []categoryDTO
			if err := resp.Into(&cats); err != nil {
				return err
			}
			rows := make([][]string, 0, len(cats))
			for _, c := range cats {
				yes := ""
				if c.IsDefault {
					yes = "是"
				}
				rows = append(rows, []string{itoa(c.ID), c.Name, c.Type, yes})
			}
			app.R.Table([]render.Col{{Title: "ID", Align: render.Right}, {Title: "名称"}, {Title: "类型"}, {Title: "默认"}}, rows)
			return nil
		},
	}
}

func ledgerTrend() *cli.Command {
	return &cli.Command{
		Name:  "trend",
		Short: "近 6 个月收支趋势",
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
			resp, err := client.Get("/api/ledger/trend", api.Query{"bookId": itoa(book.ID)}.Values())
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			if line := bookLine(book, explicit); line != "" {
				app.R.Hint(line)
			}
			var months []trendMonthDTO
			if err := resp.Into(&months); err != nil {
				return err
			}
			rows := make([][]string, 0, len(months))
			for _, m := range months {
				rows = append(rows, []string{m.Month, parse.Money(m.Income), parse.Money(m.Expense), bars(m.Expense)})
			}
			app.R.Table([]render.Col{{Title: "月份"}, {Title: "收入", Align: render.Right}, {Title: "支出", Align: render.Right}, {}}, rows)
			return nil
		},
	}
}

func ledgerBudget() *cli.Command {
	return &cli.Command{
		Name:  "budget",
		Short: "查/改当月预算",
		Long:  "查/改当月预算：留空位置参数是查询，给数字则设置为当月预算。",
		Args:  []cli.Arg{{Name: "金额", Optional: true}},
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
			if in.Arg(0) == "" {
				resp, err := client.Get("/api/ledger/budget", api.Query{"bookId": itoa(book.ID)}.Values())
				if err != nil {
					return err
				}
				if app.isJSON() {
					return app.R.Data(resp.Data)
				}
				if line := bookLine(book, explicit); line != "" {
					app.R.Hint(line)
				}
				var data budgetDTO
				if err := resp.Into(&data); err != nil {
					return err
				}
				app.R.Log(fmt.Sprintf("%s 当月预算：%s", book.Name, parse.MoneyOf(data.Budget)))
				return nil
			}
			amount, err := strconv.ParseFloat(in.Arg(0), 64)
			if err != nil {
				return cli.Usagef("预算金额需为数字，当前为 %q", in.Arg(0))
			}
			resp, err := client.Put("/api/ledger/budget", map[string]any{"bookId": book.ID, "amount": amount})
			if err != nil {
				return err
			}
			if app.isJSON() {
				return app.R.Data(resp.Data)
			}
			var data budgetDTO
			if err := resp.Into(&data); err != nil {
				return err
			}
			app.R.OK(fmt.Sprintf("%s 当月预算已设为 %s", book.Name, parse.MoneyOf(data.Budget)))
			return nil
		},
	}
}

func optionalDate(raw, label string) (string, error) {
	if raw == "" {
		return "", nil
	}
	return parse.Date(raw, label)
}

func noteSuffix(note string) string {
	if note == "" {
		return ""
	}
	return " · " + note
}
