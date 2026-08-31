package cli

import (
	"errors"
	"strconv"
	"strings"
	"testing"
)

// 测试用命令树：lair [-v] ledger add <金额> [-t] [--tag...]n [--json] [--page] cal list --day
func tree(log *[]string) *Command {
	add := &Command{
		Name:  "add",
		Short: "记一笔账",
		Args:  []Arg{{Name: "金额"}},
		Flags: []*Flag{
			{Name: "type", Short: "t", Usage: "收支", Kind: String},
			{Name: "tag", Usage: "标签", Kind: Strings},
			{Name: "page", Usage: "页码", Kind: Int, Default: 1},
			{Name: "size", Usage: "条数", Kind: Float, Default: 20.0},
			{Name: "strict", Usage: "严格模式", Kind: Bool, Default: true},
			{Name: "book", Short: "b", Usage: "账本", Kind: Int},
		},
		Run: func(ctx *Context, in *Inv) error {
			*log = append(*log,
				"args="+strings.Join(in.Args, "|"),
				"type="+in.Str("type"),
				"tags="+strings.Join(in.List("tag"), ","),
				"page="+itoa64(in.Int("page")),
				"size="+ftoa64(in.Float("size")),
				"strict="+btoa(in.Bool("strict")),
				"hasBook="+btoa(in.Has("book")),
				"verbose="+btoa(in.Bool("verbose")),
			)
			return nil
		},
	}
	ws := &Command{
		Name: "ws",
		Args: []Arg{{Name: "正文", Variadic: true}},
		Run: func(ctx *Context, in *Inv) error {
			*log = append(*log, "rest="+strings.Join(in.Rest(0), "+"))
			return nil
		},
	}
	ledger := &Command{Name: "ledger", Short: "记账", Sub: []*Command{add}}
	return &Command{
		Name:  "lair",
		Short: "测试根",
		Flags: []*Flag{{Name: "verbose", Short: "v", Usage: "详细", Kind: Bool}},
		Sub:   []*Command{ledger, ws},
	}
}

func run(t *testing.T, root *Command, args ...string) (error, string, string) {
	t.Helper()
	var out, errw strings.Builder
	err := Execute(root, args, &Context{Out: &out, Err: &errw, In: strings.NewReader("")})
	return err, out.String(), errw.String()
}

func invoke(t *testing.T, args ...string) []string {
	t.Helper()
	var log []string
	tree := tree(&log)
	err, _, errw := run(t, tree, args...)
	if err != nil {
		t.Fatalf("执行 %v 失败: %v\n%s", args, err, errw)
	}
	return log
}

func joined(log []string) string { return strings.Join(log, "\n") }

func TestFlagsAnywhereAndDefaults(t *testing.T) {
	log := invoke(t, "ledger", "add", "12.5")
	got := joined(log)
	for _, want := range []string{"args=12.5", "type=", "page=1", "size=20", "strict=true", "hasBook=false", "verbose=false"} {
		if !strings.Contains(got, want) {
			t.Errorf("缺少 %q，实际:\n%s", want, got)
		}
	}
}

func TestGlobalFlagAfterSubcommand(t *testing.T) {
	log := invoke(t, "-v", "ledger", "add", "1")
	if !strings.Contains(joined(log), "verbose=true") {
		t.Fatalf("-v 应被识别:\n%s", joined(log))
	}
	log = invoke(t, "ledger", "add", "1", "--verbose")
	if !strings.Contains(joined(log), "verbose=true") {
		t.Fatalf("全局选项写在子命令后也应生效:\n%s", joined(log))
	}
}

func TestFlagValueForms(t *testing.T) {
	log := invoke(t, "ledger", "add", "1", "-t", "支出", "--tag", "a", "--tag=b", "--page", "3", "--size", "1.5", "--strict=false", "-b", "7")
	got := joined(log)
	for _, want := range []string{"type=支出", "tags=a,b", "page=3", "size=1.5", "strict=false", "hasBook=true"} {
		if !strings.Contains(got, want) {
			t.Errorf("缺少 %q，实际:\n%s", want, got)
		}
	}
}

// "-" 本身是"支出"的别名，不能被当成选项开头。
func TestDashAsValue(t *testing.T) {
	log := invoke(t, "ledger", "add", "1", "-t", "-")
	if !strings.Contains(joined(log), "type=-") {
		t.Fatalf("-t - 应取到 \"-\":\n%s", joined(log))
	}
}

func TestDoubleDashStopsParsing(t *testing.T) {
	log := invoke(t, "ws", "--", "-not-a-flag", "第二句")
	if !strings.Contains(joined(log), "rest=-not-a-flag+第二句") {
		t.Fatalf("-- 之后的 token 应全走位置参数:\n%s", joined(log))
	}
}

func TestVariadicArgs(t *testing.T) {
	log := invoke(t, "ws", "记一下", "今天", "开会")
	if !strings.Contains(joined(log), "rest=记一下+今天+开会") {
		t.Fatalf("变长位置参数不对:\n%s", joined(log))
	}
}

func TestUsageErrors(t *testing.T) {
	cases := []struct {
		name string
		args []string
		want string
	}{
		{"未知长选项", []string{"ledger", "add", "1", "--nope"}, "未知选项 --nope"},
		{"未知短选项", []string{"ledger", "add", "1", "-z"}, "未知选项 -z"},
		// --verbose 是长选项，不能靠短名 -v 的长写法命中。
		{"长选项不吃短名", []string{"ledger", "add", "1", "--v"}, "未知选项 --v"},
		{"选项缺值", []string{"ledger", "add", "1", "--type"}, "--type 需要一个字符串"},
		{"缺位置参数", []string{"ledger", "add"}, "缺少参数 <金额>"},
		{"多余位置参数", []string{"ledger", "add", "1", "2"}, "多余参数：2"},
		{"未知子命令", []string{"ledger", "nope"}, "未知子命令：nope"},
		{"开关带非法值", []string{"ledger", "add", "1", "--strict=maybe"}, "--strict 是开关选项"},
	}
	root := tree(&[]string{})
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err, _, _ := run(t, root, tc.args...)
			var usage *UsageError
			if err == nil {
				t.Fatalf("%v 应报用法错误", tc.args)
			}
			if !errors.As(err, &usage) {
				t.Fatalf("应返回 *UsageError，实际 %T: %v", err, err)
			}
			if !strings.Contains(usage.Msg, tc.want) {
				t.Errorf("报错应含 %q，实际 %q", tc.want, usage.Msg)
			}
		})
	}
}

func TestHelpEverywhere(t *testing.T) {
	root := tree(&[]string{})
	cases := [][]string{
		{"--help"},
		{},
		{"ledger"},
		{"ledger", "--help"},
		{"ledger", "add", "--help"},
		{"ledger", "add", "-h"},
	}
	for _, args := range cases {
		err, out, _ := run(t, root, args...)
		if err != nil {
			t.Fatalf("%v 应正常退出 0，实际 %v", args, err)
		}
		if !strings.Contains(out, "用法:") {
			t.Fatalf("%v 没打出帮助:\n%s", args, out)
		}
	}
	err, out, _ := run(t, root, "ledger", "add", "--help")
	_ = err
	if !strings.Contains(out, "全局选项:") || !strings.Contains(out, "-v, --verbose") {
		t.Fatalf("叶子命令帮助应附带全局选项一节:\n%s", out)
	}
	if strings.Contains(out, "参数:") {
		t.Fatalf("位置参数已在用法行体现，不该重复一节:\n%s", out)
	}
}

// 帮助里写了 --page 却解析不了，是最典型的实现与文档脱节。
func TestHelpMatchesParsableFlags(t *testing.T) {
	root := tree(&[]string{})
	_, out, _ := run(t, root, "ledger", "add", "--help")
	for _, name := range []string{"--type", "--tag", "--page", "--size", "--strict", "--book"} {
		if !strings.Contains(out, name) {
			t.Errorf("帮助里应有 %s:\n%s", name, out)
		}
	}
	log := invoke(t, "ledger", "add", "1", "--book", "2")
	if !strings.Contains(joined(log), "hasBook=true") {
		t.Fatal("--book 应可解析")
	}
}

func TestGroupWithoutArgsPrintsHelp(t *testing.T) {
	root := tree(&[]string{})
	err, out, _ := run(t, root, "ledger")
	if err != nil {
		t.Fatalf("分组命令无参数应打帮助而不是报错: %v", err)
	}
	if !strings.Contains(out, "子命令:") || !strings.Contains(out, "add") {
		t.Fatalf("分组帮助应列出子命令:\n%s", out)
	}
}

func itoa64(v int64) string { return strconv.FormatInt(v, 10) }

func ftoa64(v float64) string { return strconv.FormatFloat(v, 'f', -1, 64) }

func btoa(v bool) string {
	if v {
		return "true"
	}
	return "false"
}
