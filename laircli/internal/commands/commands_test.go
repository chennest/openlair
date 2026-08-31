package commands

import (
	"encoding/json"
	"os"
	"strings"
	"testing"
	"time"

	"laircli/internal/cli"
	"laircli/internal/config"
)

func (f *fake) called(want string) bool {
	for _, call := range f.calls {
		if call == want {
			return true
		}
	}
	return false
}

func (f *fake) writeCalls() []string {
	var out []string
	for _, call := range f.calls {
		if strings.HasPrefix(call, "POST ") || strings.HasPrefix(call, "PUT ") || strings.HasPrefix(call, "DELETE ") {
			out = append(out, call)
		}
	}
	return out
}

func (f *fake) lastQuery() string {
	if len(f.queries) == 0 {
		return ""
	}
	return f.queries[len(f.queries)-1]
}

func mustCode(t *testing.T, got int, want int, out, errw string) {
	t.Helper()
	if got != want {
		t.Fatalf("退出码 %d，期望 %d\nstdout:\n%s\nstderr:\n%s", got, want, out, errw)
	}
}

func mustContain(t *testing.T, haystack string, needles ...string) {
	t.Helper()
	for _, needle := range needles {
		if !strings.Contains(haystack, needle) {
			t.Fatalf("输出缺少 %q\n实际:\n%s", needle, haystack)
		}
	}
}

// ---------- 配置与鉴权 ----------

func TestNotConfiguredExitsThree(t *testing.T) {
	f := newFake(t)
	f.isolate()
	var out, errw strings.Builder
	code := Run([]string{"ledger", "list"}, &cli.Context{Out: &out, Err: &errw, In: strings.NewReader("")}, false)
	mustCode(t, code, 3, out.String(), errw.String())
	mustContain(t, errw.String(), "尚未配置 API Key", "lair init")
	if f.called("GET /api/books") {
		t.Fatal("未配置时不该发请求")
	}
}

func TestUnauthorizedHintsAtReinit(t *testing.T) {
	f := newFake(t)
	f.unauthorized = true
	code, out, errw := f.run(t, "whoami")
	mustCode(t, code, 1, out, errw)
	mustContain(t, errw, "[401]", "lair init")
}

func TestInitWritesConfigOnlyAfterVerification(t *testing.T) {
	f := newFake(t)
	f.isolate()
	key := "ol_1234567890abcdef1234567890abcdef"
	var out, errw strings.Builder
	code := Run([]string{"--api-key", key, "--base-url", f.server.URL, "init"},
		&cli.Context{Out: &out, Err: &errw, In: strings.NewReader(key + "\n" + f.server.URL + "\n")}, false)
	mustCode(t, code, 0, out.String(), errw.String())
	mustContain(t, out.String(), "已连接", "小明")

	saved, err := config.Load()
	if err != nil {
		t.Fatal(err)
	}
	if saved.APIKey != key || saved.BaseURL != f.server.URL || saved.User != "小明" {
		t.Fatalf("配置没写全: %+v", saved)
	}
}

func TestInitRejectsNonKeyWithoutWriting(t *testing.T) {
	f := newFake(t)
	path := f.isolate()
	var out, errw strings.Builder
	code := Run([]string{"--api-key", "sk-wrong-prefix", "init"},
		&cli.Context{Out: &out, Err: &errw, In: strings.NewReader("")}, false)
	mustCode(t, code, 1, out.String(), errw.String())
	mustContain(t, errw.String(), "ol_")
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("校验失败时不该落盘: %v", err)
	}
}

func TestConfigShowMasksAPIKey(t *testing.T) {
	f := newFake(t)
	f.isolate()
	if _, err := config.Merge(config.File{APIKey: "ol_1234567890abcdef", BaseURL: "https://lair.example"}); err != nil {
		t.Fatal(err)
	}
	var out, errw strings.Builder
	code := Run([]string{"config"}, &cli.Context{Out: &out, Err: &errw, In: strings.NewReader("")}, false)
	mustCode(t, code, 0, out.String(), errw.String())
	outStr := out.String()
	mustContain(t, outStr, "ol_123456789…", "https://lair.example")
	if strings.Contains(outStr, "ol_1234567890abcdef") {
		t.Fatalf("明文 Key 泄到了输出里:\n%s", outStr)
	}
}

// ---------- ledger：三条必须客户端兜住的语义 ----------

func TestLedgerListDefaultsToFirstPersonalBook(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "list")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "账本：日常（#1）", "用 lair book use <id> 设默认", "午饭", "38.50", "收入 1,200.00", "当月预算 3,000.00")
	if !strings.Contains(f.lastQuery(), "bookId=1") {
		t.Fatalf("默认账本没传下去: %s", f.lastQuery())
	}
	if strings.Contains(out, "#2 家庭") {
		t.Fatalf("默认不该挑共享账本:\n%s", out)
	}
}

func TestLedgerListUsesConfiguredDefaultBook(t *testing.T) {
	f := newFake(t)
	f.isolate()
	if _, err := config.Merge(config.File{BookID: 2}); err != nil {
		t.Fatal(err)
	}
	code, out, errw := f.runRaw(t, "ledger", "list", "--book", "2")
	mustCode(t, code, 0, out, errw)
	if strings.Contains(out, "设默认") {
		t.Fatalf("显式指定账本时不该再提示设默认:\n%s", out)
	}
	if !strings.Contains(f.lastQuery(), "bookId=2") {
		t.Fatalf("--book 没生效: %s", f.lastQuery())
	}
}

func TestLedgerAddResolvesCategoryNameToID(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "add", "38.5", "-c", "餐饮", "-n", "午饭")
	mustCode(t, code, 0, out, errw)
	// 日期由服务端补，回执里带上；这里只钉住"分类名 + 备注"都在。
	if !strings.Contains(out, "#101 已记 支出 38.50 · 餐饮 · ") || !strings.HasSuffix(strings.TrimSpace(out), "午饭") {
		t.Fatalf("回执行不对: %q", out)
	}
	if !f.called("POST /api/ledger") {
		t.Fatal("没发写请求")
	}
	var body map[string]any
	if err := json.Unmarshal([]byte(f.lastBody()), &body); err != nil {
		t.Fatal(err)
	}
	if got := body["categoryId"]; got != float64(1) {
		t.Fatalf("categoryId 应由分类名解析出来: %#v", body)
	}
	if body["type"] != "支出" {
		t.Fatalf("type 应为中文枚举: %#v", body)
	}
	if _, ok := body["date"]; ok {
		t.Fatalf("未给 --date 时不该发 date: %#v", body)
	}
}

func TestLedgerAddInfersTypeFromCategorySide(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "add", "8000", "-c", "工资")
	mustCode(t, code, 0, out, errw)
	if !strings.Contains(f.lastBody(), `"type":"收入"`) {
		t.Fatalf("只给收入侧分类时应推断为收入: %s", f.lastBody())
	}
	if !strings.Contains(f.lastBody(), `"categoryId":11`) {
		t.Fatalf("categoryId 不对: %s", f.lastBody())
	}
}

func TestLedgerAddWithoutCategoryFallsBackToExpense(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "add", "10")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "未指定分类，服务端按「其他」入账")
	if strings.Contains(f.lastBody(), "categoryId") {
		t.Fatalf("没给分类时不该发 categoryId: %s", f.lastBody())
	}
	if !strings.Contains(f.lastBody(), `"type":"支出"`) {
		t.Fatalf("默认应为支出: %s", f.lastBody())
	}
}

// 后端 POST /api/ledger 不读 category 名字，省略 categoryId 会静默记成「其他」，
// 所以解析不到分类时必须一个写请求都不发。
func TestLedgerAddRejectsUnknownCategoryWithoutWriting(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "add", "10", "-c", "不存在的分类")
	mustCode(t, code, 1, out, errw)
	mustContain(t, errw, "分类「不存在的分类」不在", "餐饮")
	if writes := f.writeCalls(); len(writes) != 0 {
		t.Fatalf("分类解析失败时不该有写请求: %v", writes)
	}
}

func TestLedgerAddRejectsCrossSideCategory(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "add", "10", "-t", "支出", "-c", "工资")
	mustCode(t, code, 1, out, errw)
	mustContain(t, errw, "「支出」")
	if writes := f.writeCalls(); len(writes) != 0 {
		t.Fatalf("分类与收支方向冲突时不该写: %v", writes)
	}
}

func TestLedgerAddRejectsUnknownType(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "add", "10", "-t", "转账")
	mustCode(t, code, 1, out, errw)
	mustContain(t, errw, "类型不合法")
}

func TestLedgerAddAcceptsTypeAliases(t *testing.T) {
	for _, tc := range []struct{ flag, want string }{{"-", "支出"}, {"+", "收入"}, {"income", "收入"}, {"EXPENSE", "支出"}} {
		f := newFake(t)
		code, out, errw := f.run(t, "ledger", "add", "10", "-t", tc.flag)
		mustCode(t, code, 0, out, errw)
		if !strings.Contains(f.lastBody(), `"type":"`+tc.want+`"`) {
			t.Errorf("%s 应映射成 %s，实际 %s", tc.flag, tc.want, f.lastBody())
		}
	}
}

func TestLedgerAddRelativeDate(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "add", "10", "-d", "昨天")
	mustCode(t, code, 0, out, errw)
	yesterday := time.Now().AddDate(0, 0, -1).Format("2006-01-02")
	if !strings.Contains(f.lastBody(), `"date":"`+yesterday+`"`) {
		t.Fatalf("--date 昨天 没展开: %s", f.lastBody())
	}
}

func TestLedgerAddRejectsBadDate(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "add", "10", "-d", "上礼拜")
	mustCode(t, code, 1, out, errw)
	mustContain(t, errw, "--date 需为 YYYY-MM-DD")
}

func TestLedgerAddRejectsNonNumericAmount(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "add", "十块")
	mustCode(t, code, 2, out, errw)
	mustContain(t, errw, "金额需为数字")
}

func TestLedgerEditGuards(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "edit", "9", "-c", "交通")
	mustCode(t, code, 2, out, errw)
	mustContain(t, errw, "改分类需同时给 --type")

	code, out, errw = f.run(t, "ledger", "edit", "9")
	mustCode(t, code, 2, out, errw)
	mustContain(t, errw, "至少要给一个修改项")

	code, out, errw = f.run(t, "ledger", "edit", "abc", "--amount", "3")
	mustCode(t, code, 2, out, errw)
	mustContain(t, errw, "需为整数")

	code, out, errw = f.run(t, "ledger", "edit", "9", "--amount", "12", "-t", "支出", "-c", "交通")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "#9 已更新 → 支出 12.00 · 交通")
	if !strings.Contains(f.lastBody(), `"categoryId":2`) {
		t.Fatalf("categoryId 没解析: %s", f.lastBody())
	}
}

func TestLedgerRemove(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "rm", "9")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "#9 已删除")
	if !f.called("DELETE /api/ledger/9") {
		t.Fatalf("没打到删除接口: %v", f.calls)
	}
}

func TestLedgerCategoriesAndTrend(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "categories", "-t", "收入")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "工资", "其他")
	if strings.Contains(out, "餐饮") {
		t.Fatalf("--type 收入 时不该出现支出侧分类:\n%s", out)
	}

	f = newFake(t)
	code, out, errw = f.run(t, "ledger", "trend")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "2026-07", "2026-08")
	if !strings.Contains(out, strings.Repeat("█", 3)) {
		t.Fatalf("640 元支出应画 3 格: %q", out)
	}
}

func TestLedgerBudgetReadAndWrite(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "ledger", "budget")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "当月预算：-")

	f = newFake(t)
	code, out, errw = f.run(t, "ledger", "budget", "5000")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "已设为 5,000.00")
	if !strings.Contains(f.lastBody(), `"amount":5000`) {
		t.Fatalf("预算没发出去: %s", f.lastBody())
	}
}

// ---------- JSON 输出与错误归一 ----------

func TestJSONStdoutIsPureAndComplete(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "--json", "ledger", "list")
	mustCode(t, code, 0, out, errw)
	if strings.Contains(out, "账本：") || strings.Contains(out, "收入 1,200.00") {
		t.Fatalf("JSON 模式 stdout 混进了人类提示:\n%s", out)
	}
	var page map[string]any
	if err := json.Unmarshal([]byte(out), &page); err != nil {
		t.Fatalf("stdout 不是合法 JSON: %v\n%s", err, out)
	}
	// 原始 data 直出：categoryStats 这类 CLI 没建模的字段也必须保留。
	if _, ok := page["summary"]; !ok {
		t.Fatalf("summary 丢了: %s", out)
	}
	if _, ok := page["pageSize"]; !ok {
		t.Fatalf("pageSize 丢了: %s", out)
	}
}

func TestEnvVarJSONEquivalent(t *testing.T) {
	f := newFake(t)
	f.isolate()
	t.Setenv("LAIRCLI_JSON", "1")
	code, out, errw := f.runRaw(t, "ledger", "categories")
	mustCode(t, code, 0, out, errw)
	var cats []map[string]any
	if err := json.Unmarshal([]byte(out), &cats); err != nil {
		t.Fatalf("LAIRCLI_JSON=1 应等价 --json: %v\n%s", err, out)
	}
}

// 422 是唯一不走统一信封的失败（后端没注册 RequestValidationError handler），
// 裸 {"detail":[...]} 也必须被归一成一行可读文案。
func TestUnprocessableDetailBecomesReadable(t *testing.T) {
	f := newFake(t)
	f.unprocessable = true
	code, out, errw := f.run(t, "ledger", "add", "10", "-c", "餐饮")
	mustCode(t, code, 1, out, errw)
	mustContain(t, errw, "[422] 参数不合法", "amount: Input should be a valid number")
	if strings.Contains(errw, "body.amount") {
		t.Fatalf("loc 前缀没去掉: %s", errw)
	}
}

func TestNotFoundMessage(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "note", "show", "99")
	mustCode(t, code, 1, out, errw)
	mustContain(t, errw, "笔记 99 不存在")
}

func TestVerbosePrintsRequestOutlineToStderr(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "-v", "ledger", "list")
	mustCode(t, code, 0, out, errw)
	mustContain(t, errw, "GET /api/books → 200", "GET /api/ledger → 200")
	if strings.Contains(out, "→ 200") {
		t.Fatalf("调试信息不该进 stdout:\n%s", out)
	}
}

func TestUnreachableHostMessage(t *testing.T) {
	f := newFake(t)
	f.isolate()
	var out, errw strings.Builder
	code := Run([]string{"--api-key", "ol_x", "--base-url", "http://127.0.0.1:1", "book", "list"},
		&cli.Context{Out: &out, Err: &errw, In: strings.NewReader("")}, false)
	mustCode(t, code, 1, out.String(), errw.String())
	mustContain(t, errw.String(), "连不上 http://127.0.0.1:1")
}

// ---------- 其余模块 ----------

func TestTodoModule(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "todo", "list")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "交房租", "回邮件", "重要不紧急")

	f = newFake(t)
	code, out, errw = f.run(t, "todo", "list", "--open")
	mustCode(t, code, 0, out, errw)
	if strings.Contains(out, "回邮件") {
		t.Fatalf("--open 应过滤已完成:\n%s", out)
	}

	f = newFake(t)
	code, out, errw = f.run(t, "todo", "add", "交房租", "-q", "2", "-d", "本周五")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "#31 已添加：交房租（重要不紧急")
	if !strings.Contains(f.lastBody(), `"quadrant":"重要不紧急"`) {
		t.Fatalf("象限数字别名没映射: %s", f.lastBody())
	}

	f = newFake(t)
	code, out, errw = f.run(t, "todo", "add", "x", "-q", "9")
	mustCode(t, code, 1, out, errw)
	mustContain(t, errw, "象限不合法")

	f = newFake(t)
	code, out, errw = f.run(t, "todo", "done", "1")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "#1 已完成")
	if !strings.Contains(f.lastBody(), `"done":true`) {
		t.Fatalf("done 没传: %s", f.lastBody())
	}
}

func TestCalModule(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "cal", "list")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "周会", "体检")
	if strings.Index(out, "周会") > strings.Index(out, "体检") {
		t.Fatalf("应按日期升序:\n%s", out)
	}

	f = newFake(t)
	code, out, errw = f.run(t, "cal", "list", "--day", "今天")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "周会")
	if strings.Contains(out, "体检") {
		t.Fatalf("--day 今天 不该带出其他日期:\n%s", out)
	}

	f = newFake(t)
	code, out, errw = f.run(t, "cal", "list", "--open")
	mustCode(t, code, 0, out, errw)
	if strings.Contains(out, "体检") {
		t.Fatalf("--open 应过滤已完成:\n%s", out)
	}

	f = newFake(t)
	code, out, errw = f.run(t, "cal", "add", "评审", "-d", "明天", "-T", "14:00", "-l", "线上")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "#41 已安排")
	tomorrow := time.Now().AddDate(0, 0, 1).Format("2006-01-02")
	for _, want := range []string{`"date":"` + tomorrow + `"`, `"time":"14:00"`, `"location":"线上"`} {
		if !strings.Contains(f.lastBody(), want) {
			t.Errorf("请求体缺 %s：%s", want, f.lastBody())
		}
	}
}

func TestNoteModule(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "note", "list")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "周记", "工作 复盘")
	if strings.Contains(out, "很长的一段笔记内容很长的一段笔记内容很长的一段笔记内容") {
		t.Fatalf("摘要应被截断:\n%s", out)
	}

	f = newFake(t)
	code, out, errw = f.run(t, "note", "show", "1")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "周记", "#工作 复盘", strings.Repeat("很长的一段笔记内容", 12))

	f = newFake(t)
	code, out, errw = f.run(t, "note", "add", "买", "牛奶", "--title", "清单", "--tag", "生活", "--tag", "紧急")
	mustCode(t, code, 0, out, errw)
	var body map[string]any
	if err := json.Unmarshal([]byte(f.lastBody()), &body); err != nil {
		t.Fatal(err)
	}
	if body["summary"] != "买 牛奶" {
		t.Fatalf("多词正文应空格拼接: %#v", body["summary"])
	}
	tags, _ := body["tags"].([]any)
	if len(tags) != 2 || tags[0] != "生活" {
		t.Fatalf("--tag 应可重复: %#v", body["tags"])
	}

	f = newFake(t)
	code, out, errw = f.run(t, "note", "add")
	mustCode(t, code, 2, out, errw)
}

func TestHabitModule(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "habit", "list")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "早起", "3 天", "▰▰▰▱▱▱▱")

	f = newFake(t)
	code, out, errw = f.run(t, "habit", "check", "1")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "早起 今日已打卡（当前连续 4 天）")
	// 后端 update 不重算 week，所以打卡输出里不该有本周格子。
	if strings.Contains(out, "▰") {
		t.Fatalf("打卡输出不该画本周格子:\n%s", out)
	}

	f = newFake(t)
	code, out, errw = f.run(t, "habit", "add", "跑步")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "#3 已新建习惯：跑步")
}

func TestBookModule(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "book", "list")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "日常", "个人", "家庭", "共享", "小明")

	f = newFake(t)
	code, out, errw = f.run(t, "book", "create", "旅行", "-t", "shared")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "账本 #3 旅行 已创建")
	if !strings.Contains(f.lastBody(), `"type":"shared"`) {
		t.Fatalf("类型没传: %s", f.lastBody())
	}

	f = newFake(t)
	code, out, errw = f.run(t, "book", "create", "旅行", "-t", "全家桶")
	mustCode(t, code, 2, out, errw)

	f = newFake(t)
	code, out, errw = f.run(t, "book", "current")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "当前账本：#1 日常（个人）· 来源：自动取首个个人账本")

	f = newFake(t)
	code, out, errw = f.run(t, "--json", "book", "current", "-b", "2")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, `"source": "命令行 --book / 配置默认"`)

	f = newFake(t)
	code, out, errw = f.run(t, "book", "join", "ABCD1234")
	mustCode(t, code, 0, out, errw)
	if !f.called("POST /api/books/join") || !strings.Contains(f.lastBody(), `"code":"ABCD1234"`) {
		t.Fatalf("加入账本没发对: %v %s", f.calls, f.lastBody())
	}
}

func TestBookUsePersistsDefault(t *testing.T) {
	f := newFake(t)
	f.isolate()
	code, out, errw := f.runRaw(t, "book", "use", "2")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "默认账本已切换为 #2 家庭")
	saved, err := config.Load()
	if err != nil {
		t.Fatal(err)
	}
	if saved.BookID != 2 {
		t.Fatalf("book_id 没落盘: %+v", saved)
	}

	f = newFake(t)
	f.isolate()
	code, out, errw = f.runRaw(t, "book", "use", "99")
	mustCode(t, code, 1, out, errw)
	mustContain(t, errw, "账本 99 不存在")
	saved, _ = config.Load()
	if saved.BookID != 0 {
		t.Fatalf("校验失败不该改默认账本: %+v", saved)
	}
}

func TestOverview(t *testing.T) {
	f := newFake(t)
	code, out, errw := f.run(t, "overview")
	mustCode(t, code, 0, out, errw)
	mustContain(t, out, "本月支出 1,250.00 ↓12.5% （预算 3,000，已用 42%）", "交房租", "即将开始", "（无）", "✓ 早起")
}

// ---------- 刻意不做的能力 ----------

func TestSensitiveCommandsAreGone(t *testing.T) {
	cases := [][]string{
		{"api", "GET", "/api/books"},
		{"keys", "list"},
		{"keys", "create", "笔记本"},
		{"keys", "revoke", "1"},
		{"book", "delete", "1"},
		{"book", "purge", "1"},
		{"book", "trash"},
		{"book", "invite", "1", "--rotate"},
		{"book", "members", "1"},
		{"config", "set", "api_key", "ol_x"},
		{"config", "unset", "book_id"},
		{"ask", "帮我记一笔"},
		{"snap", "午饭38"},
		{"transcribe", "./a.wav"},
	}
	for _, args := range cases {
		f := newFake(t)
		code, out, errw := f.run(t, args...)
		mustCode(t, code, 2, out, errw)
		if f.called("POST /api/ledger") {
			t.Fatalf("%v 不该产生写请求", args)
		}
	}
}
