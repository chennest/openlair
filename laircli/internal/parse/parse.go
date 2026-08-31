// Package parse 收拢"命令行写法 → 后端要的值"这一层的语义。
//
// 后端事实决定了这里不能偷懒：
//   - transactions.type 实际存的是中文枚举（「支出」/「收入」），且服务端会把一切非「收入」
//     的值悄悄归成「支出」，所以未知值必须在这里拒绝。
//   - 待办象限同样是固定中文枚举。
package parse

import (
	"fmt"
	"strconv"
	"strings"
	"time"
)

const (
	Income  = "收入"
	Expense = "支出"
)

// Quadrants 与后端 QUADRANTS 顺序一致，下标即 --quadrant 的数字别名。
var Quadrants = []string{"重要紧急", "重要不紧急", "紧急不重要", "不重要不紧急"}

var typeAliases = map[string]string{
	"expense": Expense,
	"exp":     Expense,
	"out":     Expense,
	"-":       Expense,
	"支出":      Expense,
	"花":       Expense,
	"income":  Income,
	"inc":     Income,
	"in":      Income,
	"+":       Income,
	"收入":      Income,
}

// Type 把 -t expense|收入|- 映射成后端要求的中文枚举；不接受的值直接报错。
func Type(raw string) (string, error) {
	value := strings.TrimSpace(raw)
	if hit, ok := typeAliases[strings.ToLower(value)]; ok {
		return hit, nil
	}
	if hit, ok := typeAliases[value]; ok {
		return hit, nil
	}
	return "", fmt.Errorf("类型不合法：%s（可选 expense / income，或 支出 / 收入）", raw)
}

// Quadrant 支持 1-4 数字别名、精确中文名，以及唯一前缀（如 重要不 → 有歧义时报错）。
func Quadrant(raw string) (string, error) {
	value := strings.TrimSpace(raw)
	if digitsOnly(value) {
		if idx, err := strconv.Atoi(value); err == nil && idx >= 1 && idx <= len(Quadrants) {
			return Quadrants[idx-1], nil
		}
	}
	for _, q := range Quadrants {
		if q == value {
			return q, nil
		}
	}
	var hits []string
	for _, q := range Quadrants {
		if strings.HasPrefix(q, value) && value != "" {
			hits = append(hits, q)
		}
	}
	if len(hits) == 1 {
		return hits[0], nil
	}
	if len(hits) > 1 {
		return "", fmt.Errorf("象限「%s」有歧义：%s", value, strings.Join(hits, "、"))
	}
	return "", fmt.Errorf("象限不合法：%s（可选 1-4 或 %s）", raw, strings.Join(Quadrants, "、"))
}

// Date 接受 YYYY-MM-DD 与 今天/昨天/明天，返回规范化后的日期串。
func Date(raw, label string) (string, error) {
	value := strings.TrimSpace(raw)
	today := time.Now()
	switch value {
	case "今天", "today":
		return formatDate(today), nil
	case "昨天", "yesterday":
		return formatDate(today.AddDate(0, 0, -1)), nil
	case "明天", "tomorrow":
		return formatDate(today.AddDate(0, 0, 1)), nil
	}
	// time.Parse 对 "2006-01-02" 会放过 2025-1-2 这类非补零写法，后端日期字段会收不下，
	// 所以先按定长格式硬校验。
	if len(value) != 10 || value[4] != '-' || value[7] != '-' {
		return "", fmt.Errorf("%s 需为 YYYY-MM-DD，当前为 %q", label, raw)
	}
	parsed, err := time.Parse("2006-01-02", value)
	if err != nil {
		return "", fmt.Errorf("%s 需为 YYYY-MM-DD，当前为 %q", label, raw)
	}
	return parsed.Format("2006-01-02"), nil
}

// Money 把金额渲染成千分位两位小数。
func Money(amount float64) string {
	return group(fmt.Sprintf("%.2f", amount))
}

// MoneyOf 渲染可空金额，缺失时给 "-"（例如预算未设置时后端返回 null）。
func MoneyOf(amount *float64) string {
	if amount == nil {
		return "-"
	}
	return Money(*amount)
}

// MoneyNoCents 用于总览里的预算这类整数口径（对齐 Python 的 {:,.0f}）。
func MoneyNoCents(amount float64) string {
	return group(fmt.Sprintf("%.0f", amount))
}

func formatDate(t time.Time) string { return t.Format("2006-01-02") }

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

// group 给 "1234.56" 这样的整小数串插入千分位逗号。
func group(decimal string) string {
	sign := ""
	if strings.HasPrefix(decimal, "-") {
		sign, decimal = "-", decimal[1:]
	}
	integer, fraction := decimal, ""
	if idx := strings.Index(decimal, "."); idx >= 0 {
		integer, fraction = decimal[:idx], decimal[idx:]
	}
	var out strings.Builder
	for i, r := range integer {
		if i > 0 && (len(integer)-i)%3 == 0 {
			out.WriteByte(',')
		}
		out.WriteRune(r)
	}
	return sign + out.String() + fraction
}
