package parse

import (
	"testing"
	"time"
)

func TestTypeAliases(t *testing.T) {
	cases := map[string]string{
		"expense": Expense, "EXPENSE": Expense, "exp": Expense, "out": Expense, "-": Expense,
		"支出": Expense, "花": Expense, " 支出 ": Expense,
		"income": Income, "Income": Income, "inc": Income, "in": Income, "+": Income, "收入": Income,
	}
	for raw, want := range cases {
		got, err := Type(raw)
		if err != nil {
			t.Errorf("Type(%q) 报错: %v", raw, err)
			continue
		}
		if got != want {
			t.Errorf("Type(%q) = %q，期望 %q", raw, got, want)
		}
	}
}

// 后端会把一切非「收入」的值悄悄归成「支出」，所以未知值必须在客户端就拦住。
func TestTypeRejectsUnknown(t *testing.T) {
	for _, raw := range []string{"转账", "0", "支出收入", ""} {
		if got, err := Type(raw); err == nil {
			t.Errorf("Type(%q) 不该通过，拿到了 %q", raw, got)
		}
	}
}

func TestQuadrantNumbers(t *testing.T) {
	for i, want := range Quadrants {
		got, err := Quadrant(string(rune('1' + i)))
		if err != nil || got != want {
			t.Errorf("Quadrant(%d) = %q, %v，期望 %q", i+1, got, err, want)
		}
	}
}

func TestQuadrantNames(t *testing.T) {
	if got, err := Quadrant("重要紧急"); err != nil || got != "重要紧急" {
		t.Fatalf("精确匹配失败: %q %v", got, err)
	}
	// 「重要不」只命中「重要不紧急」，可以放行；「重要」同时命中两项，必须报歧义而不是猜一个。
	if got, err := Quadrant("重要不"); err != nil || got != "重要不紧急" {
		t.Fatalf("唯一前缀应能匹配: %q %v", got, err)
	}
	if _, err := Quadrant("重要"); err == nil {
		t.Fatal("有歧义时应报错")
	}
	for _, raw := range []string{"0", "5", "第一象限", ""} {
		if _, err := Quadrant(raw); err == nil {
			t.Errorf("Quadrant(%q) 不该通过", raw)
		}
	}
}

func TestDateRelativeWords(t *testing.T) {
	today := time.Now()
	cases := map[string]time.Time{"今天": today, "昨天": today.AddDate(0, 0, -1), "明天": today.AddDate(0, 0, 1)}
	for raw, base := range cases {
		got, err := Date(raw, "--date")
		if err != nil {
			t.Fatalf("Date(%q): %v", raw, err)
		}
		if want := base.Format("2006-01-02"); got != want {
			t.Fatalf("Date(%q) = %s，期望 %s", raw, got, want)
		}
	}
}

func TestDateISOAndErrors(t *testing.T) {
	if got, err := Date("2026-03-05", "--date"); err != nil || got != "2026-03-05" {
		t.Fatalf("ISO 日期解析失败: %q %v", got, err)
	}
	for _, raw := range []string{"2026-3-5", "2026/03/05", "2026-13-01", "下周三", ""} {
		got, err := Date(raw, "--start")
		if err == nil {
			t.Errorf("Date(%q) 不该通过，拿到了 %q", raw, got)
			continue
		}
		if got != "" {
			t.Errorf("报错时应返回空串")
		}
	}
}

// 报错文案要带上是哪个选项，用户才知道改哪里。
func TestDateErrorNamesTheOption(t *testing.T) {
	_, err := Date("乱写", "--end")
	if err == nil {
		t.Fatal("应报错")
	}
	if got := err.Error(); got != `--end 需为 YYYY-MM-DD，当前为 "乱写"` {
		t.Fatalf("文案不对: %s", got)
	}
}

func TestMoney(t *testing.T) {
	cases := map[float64]string{
		0: "0.00", 12.5: "12.50", 1234.5: "1,234.50", 1234567.891: "1,234,567.89", -42.1: "-42.10",
	}
	for in, want := range cases {
		if got := Money(in); got != want {
			t.Errorf("Money(%v) = %s，期望 %s", in, got, want)
		}
	}
}

func TestMoneyOfNil(t *testing.T) {
	if got := MoneyOf(nil); got != "-" {
		t.Fatalf("空金额应显示 -，实际 %s", got)
	}
	value := 8.0
	if got := MoneyOf(&value); got != "8.00" {
		t.Fatalf("非空金额不对: %s", got)
	}
}
