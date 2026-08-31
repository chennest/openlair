package render

import (
	"strings"
	"testing"
)

func TestWidth(t *testing.T) {
	cases := map[string]int{
		"":    0,
		"abc": 3,
		"中文":  4,
		"a中b": 4,
		"｜":   2, // 全角竖线
		"…":   1, // 省略号是 Ambiguous，按 1 列算
		"✓":   1,
		"（空）": 6,
	}
	for text, want := range cases {
		if got := Width(text); got != want {
			t.Errorf("Width(%q) = %d，期望 %d", text, got, want)
		}
	}
}

func TestTableAlignsByDisplayWidth(t *testing.T) {
	var out strings.Builder
	r := New(&out, &out, false, false)
	r.Table([]Col{{Title: "ID", Align: Right}, {Title: "分类"}, {Title: "金额", Align: Right}}, [][]string{
		{"1", "餐饮", "12.50"},
		{"100", "交通", "1,234.00"},
	})
	lines := strings.Split(strings.TrimRight(out.String(), "\n"), "\n")
	if len(lines) != 4 {
		t.Fatalf("应有表头 + 分隔线 + 2 行数据，实际 %d 行:\n%s", len(lines), out.String())
	}
	// 每行的显示宽度必须一致，否则中文列会错位。
	width := Width(lines[1])
	for _, line := range lines {
		if Width(line) != width {
			t.Fatalf("列宽不齐:\n%q\n%q", line, lines[1])
		}
	}
	if !strings.HasPrefix(lines[0], " ID") {
		t.Fatalf("ID 列右对齐后应以空格开头，实际 %q", lines[0])
	}
	if !strings.Contains(lines[3], "100") || !strings.Contains(lines[3], "交通") {
		t.Fatalf("数据行内容不对: %q", lines[3])
	}
}

func TestTableCellFallsBackToDash(t *testing.T) {
	var out strings.Builder
	New(&out, &out, false, false).Table([]Col{{Title: "备注"}}, [][]string{{""}, {"午饭"}})
	body := out.String()
	if !strings.Contains(body, "-") {
		t.Fatalf("空单元格应显示 -:\n%s", body)
	}
}

func TestTableEmpty(t *testing.T) {
	var out strings.Builder
	New(&out, &out, false, false).Table([]Col{{Title: "ID"}}, nil)
	if strings.TrimSpace(out.String()) != "（空）" {
		t.Fatalf("空表应打占位提示: %q", out.String())
	}
}

func TestQuietSuppressesHintsOnly(t *testing.T) {
	var out, errw strings.Builder
	r := New(&out, &errw, true, false)
	r.Hint("账本：日常")
	r.OK("#1 已记")
	if strings.TrimSpace(out.String()) != "#1 已记" {
		t.Fatalf("JSON 模式下 stdout 只应留结果行:\n%q", out.String())
	}
}

func TestWarningsAndFailuresGoToStderr(t *testing.T) {
	var out, errw strings.Builder
	r := New(&out, &errw, false, false)
	r.Warn("注意")
	r.Fail("炸了")
	if out.Len() != 0 {
		t.Fatalf("提示与报错不该污染 stdout: %q", out.String())
	}
	if !strings.Contains(errw.String(), "注意") || !strings.Contains(errw.String(), "炸了") {
		t.Fatalf("stderr 内容缺失: %q", errw.String())
	}
}

func TestColorOnlyWhenEnabled(t *testing.T) {
	var plainOut, colorOut strings.Builder
	New(&plainOut, &plainOut, false, false).OK("好")
	New(&colorOut, &colorOut, false, true).OK("好")
	if strings.Contains(plainOut.String(), "\x1b[") {
		t.Fatalf("管道场景不应有 ANSI: %q", plainOut.String())
	}
	if !strings.Contains(colorOut.String(), "\x1b[32m") {
		t.Fatalf("开启颜色时应染绿: %q", colorOut.String())
	}
}

// --json 要输出服务端原始字段的缩进版本：中文不转义、字段不丢。
func TestDataKeepsRawFieldsAndChinese(t *testing.T) {
	var out strings.Builder
	raw := []byte(`{"id":1,"note":"午饭","extra":{"k":[1,2]}}`)
	if err := New(&out, &out, true, false).Data(raw); err != nil {
		t.Fatal(err)
	}
	got := out.String()
	if !strings.Contains(got, `"午饭"`) {
		t.Fatalf("中文被转义了: %s", got)
	}
	if !strings.Contains(got, `"extra"`) {
		t.Fatalf("未知字段被丢了: %s", got)
	}
	if !strings.HasSuffix(got, "}\n") {
		t.Fatalf("输出应以换行收尾: %q", got)
	}
}

func TestJSONEscapesHTMLFalse(t *testing.T) {
	var out strings.Builder
	if err := New(&out, &out, true, false).JSON(map[string]any{"note": "a<b>&c"}); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out.String(), "a<b>&c") {
		t.Fatalf("不应把 <>& 转成 \\u003c: %s", out.String())
	}
}
