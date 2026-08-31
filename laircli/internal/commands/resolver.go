package commands

import (
	"fmt"
	"net/url"
	"strconv"
	"strings"

	"laircli/internal/api"
	"laircli/internal/cli"
)

// 客户端侧补齐后端没有的东西：当前账本、分类名 → id。
//
// 后端事实：ledger 系列接口缺 bookId 直接 400「缺少账本」，没有隐式默认账本；
// POST /api/ledger 的 category（名字）字段服务端根本不读，省略 categoryId 会静默落到
// 「其他」。所以这两件事必须由 CLI 兜住，解析不到就硬失败，绝不带着错值发写请求。

// resolveBook 返回 (账本, 是否显式指定)。未显式指定时取首个个人账本，语义对齐总览页。
func (a *App) resolveBook(client *api.Client, override *int) (bookDTO, bool, error) {
	var books []bookDTO
	resp, err := client.Get("/api/books", nil)
	if err != nil {
		return bookDTO{}, false, err
	}
	if err := resp.Into(&books); err != nil {
		return bookDTO{}, false, err
	}
	wanted := override
	if wanted == nil {
		wanted = a.defaultBookID()
	}
	if wanted != nil {
		for _, book := range books {
			if book.ID == *wanted {
				return book, true, nil
			}
		}
		return bookDTO{}, false, fmt.Errorf("账本 %d 不存在或你已不在其中：lair book list 看可选", *wanted)
	}
	if len(books) == 0 {
		return bookDTO{}, false, errNoBook
	}
	for _, book := range books {
		if book.Type == "personal" {
			return book, false, nil
		}
	}
	return books[0], false, nil
}

var errNoBook = fmt.Errorf("还没有账本：先运行 lair book create <名称>")

// categories 拉分类表；txType 为空表示跨收支两侧都取。
func (a *App) categories(client *api.Client, txType string) ([]categoryDTO, error) {
	query := url.Values{}
	if txType != "" {
		query.Set("type", txType)
	}
	resp, err := client.Get("/api/ledger/categories", query)
	if err != nil {
		return nil, err
	}
	var cats []categoryDTO
	if err := resp.Into(&cats); err != nil {
		return nil, err
	}
	return cats, nil
}

// pickCategory 把分类名/id 解析成 Category；解析不到就报错，避免静默记成「其他」。
//
// txType 为空时按跨侧查找，调用方可用返回的 Type 反推收支方向。
func pickCategory(cats []categoryDTO, txType, query string) (*categoryDTO, error) {
	text := strings.TrimSpace(query)
	if text == "" {
		return nil, nil
	}
	scope := ""
	if txType != "" {
		scope = fmt.Sprintf("「%s」", txType)
	}
	if digitsOnly(text) {
		want, _ := strconv.Atoi(text)
		for i := range cats {
			if cats[i].ID == want {
				return &cats[i], nil
			}
		}
		return nil, fmt.Errorf("分类 id %s 不在%s可选分类里", text, scope)
	}
	var picked []categoryDTO
	for _, exact := range cats {
		if exact.Name == text {
			picked = append(picked, exact)
		}
	}
	if len(picked) == 0 {
		for _, c := range cats {
			if strings.HasPrefix(c.Name, text) {
				picked = append(picked, c)
			}
		}
	}
	switch {
	case len(picked) == 1:
		return &picked[0], nil
	case len(picked) > 1:
		names := make([]string, 0, len(picked))
		for _, c := range picked {
			names = append(names, c.Name)
		}
		return nil, fmt.Errorf("分类「%s」有歧义：%s", text, strings.Join(names, "、"))
	}
	names := make([]string, 0, len(cats))
	for _, c := range cats {
		names = append(names, c.Name)
	}
	if len(names) == 0 {
		names = append(names, "（无可用分类）")
	}
	return nil, fmt.Errorf("分类「%s」不在%s可选分类里；可选：%s", text, scope, strings.Join(names, "、"))
}

const bookHint = "用 lair book use <id> 设默认"

func bookLine(book bookDTO, explicit bool) string {
	if explicit {
		return ""
	}
	return fmt.Sprintf("账本：%s（#%d）—— %s", book.Name, book.ID, bookHint)
}

func digitsOnly(value string) bool {
	if value == "" {
		return false
	}
	for _, r := range value {
		if r < '0' || r > '9' {
			return false
		}
	}
	return true
}

func itoa(value int) string { return strconv.Itoa(value) }

// parseID 把位置参数里的 id 转成整数；写法错误算用法错误（退出码 2），不是接口失败。
func parseID(raw, label string) (int, error) {
	id, err := strconv.Atoi(strings.TrimSpace(raw))
	if err != nil {
		return 0, cli.Usagef("%s 需为整数，当前为 %q", label, raw)
	}
	return id, nil
}

// bars 是趋势表里的支出柱状图，200 元一格，最多 30 格。
func bars(expense float64) string {
	if expense <= 0 {
		return ""
	}
	count := int(expense / 200)
	if count < 1 {
		count = 1
	}
	if count > 30 {
		count = 30
	}
	return strings.Repeat("█", count)
}

// weekBar 是习惯本周打卡条：▰ 已打卡，▱ 未打卡。
func weekBar(week []bool) string {
	var b strings.Builder
	for i, done := range week {
		if i == 7 {
			break
		}
		if done {
			b.WriteString("▰")
			continue
		}
		b.WriteString("▱")
	}
	return b.String()
}

var typeLabels = map[string]string{"personal": "个人", "shared": "共享"}

func bookTypeLabel(t string) string {
	if label, ok := typeLabels[t]; ok {
		return label
	}
	return t
}
