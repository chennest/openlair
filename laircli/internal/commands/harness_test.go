package commands

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"laircli/internal/cli"
)

// 这些用例走真实入口 commands.Run + 一个假后端：断言的是"用户能看到什么、退出码是什么、
// 到底往后端发了什么"，而不是内部函数返回值。

// fake 记录每一次调用，方便断言"分类解析失败时绝不发写请求"。
type fake struct {
	t       *testing.T
	server  *httptest.Server
	calls   []string
	bodies  []string
	queries []string

	unauthorized  bool
	unprocessable bool
}

func newFake(t *testing.T) *fake {
	t.Helper()
	f := &fake{t: t}
	f.server = httptest.NewServer(http.HandlerFunc(f.serve))
	t.Cleanup(f.server.Close)
	return f
}

func (f *fake) isolate() string {
	path := filepath.Join(f.t.TempDir(), "config.json")
	f.t.Setenv("LAIRCLI_CONFIG", path)
	f.t.Setenv("XDG_CONFIG_HOME", "")
	f.t.Setenv("OPENLAIR_API_KEY", "")
	f.t.Setenv("OPENLAIR_BASE_URL", "")
	f.t.Setenv("OPENLAIR_BOOK_ID", "")
	f.t.Setenv("LAIRCLI_JSON", "")
	return path
}

// run 用临时配置 + 显式 Key 跑一条命令，返回退出码与两路输出。
func (f *fake) run(t *testing.T, args ...string) (int, string, string) {
	t.Helper()
	f.isolate()
	return f.runRaw(t, args...)
}

func (f *fake) runRaw(t *testing.T, args ...string) (int, string, string) {
	t.Helper()
	full := append([]string{"--api-key", "ol_test_key_value", "--base-url", f.server.URL}, args...)
	var out, errw strings.Builder
	code := Run(full, &cli.Context{Out: &out, Err: &errw, In: strings.NewReader("")}, false)
	return code, out.String(), errw.String()
}

func (f *fake) record(r *http.Request, body string) {
	f.calls = append(f.calls, r.Method+" "+r.URL.Path)
	f.bodies = append(f.bodies, body)
	f.queries = append(f.queries, r.URL.RawQuery)
}

func (f *fake) lastBody() string {
	if len(f.bodies) == 0 {
		return ""
	}
	return f.bodies[len(f.bodies)-1]
}

func envelope(w http.ResponseWriter, status int, data any) {
	body, _ := json.Marshal(map[string]any{"code": status, "message": "成功", "data": data})
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	w.Write(body)
}

func fail(w http.ResponseWriter, status int, message string) {
	body, _ := json.Marshal(map[string]any{"code": status, "message": message, "data": nil})
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	w.Write(body)
}

var categories = []categoryDTO{
	{ID: 1, Name: "餐饮", Type: "支出", IsDefault: true},
	{ID: 2, Name: "交通", Type: "支出", IsDefault: true},
	{ID: 11, Name: "工资", Type: "收入", IsDefault: true},
	{ID: 16, Name: "其他", Type: "收入", IsDefault: true},
}

var books = []bookDTO{
	{ID: 1, Name: "日常", Type: "personal", Members: []memberDTO{{Role: "owner", User: userDTO{ID: 1, Name: "小明"}}}},
	{ID: 2, Name: "家庭", Type: "shared", Members: []memberDTO{{Role: "editor", User: userDTO{ID: 1, Name: "小明"}}}},
}

func (f *fake) serve(w http.ResponseWriter, r *http.Request) {
	raw, _ := io.ReadAll(r.Body)
	f.record(r, string(raw))

	if f.unauthorized {
		fail(w, http.StatusUnauthorized, "未登录或登录已过期，请重新登录")
		return
	}
	if f.unprocessable {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnprocessableEntity)
		io.WriteString(w, `{"detail":[{"type":"float_parsing","loc":["body","amount"],"msg":"Input should be a valid number","input":"abc"}]}`)
		return
	}

	switch {
	case r.Method == http.MethodGet && r.URL.Path == "/api/auth/me":
		envelope(w, 200, meDTO{ID: 1, Name: "小明", Email: "xiaoming@example.com", CreatedAt: "2026-01-02T00:00:00"})
	case r.Method == http.MethodGet && r.URL.Path == "/api/books":
		envelope(w, 200, books)
	case r.Method == http.MethodGet && r.URL.Path == "/api/ledger/categories":
		want := r.URL.Query().Get("type")
		var kept []categoryDTO
		for _, c := range categories {
			if want == "" || c.Type == want {
				kept = append(kept, c)
			}
		}
		envelope(w, 200, kept)
	case r.Method == http.MethodPost && r.URL.Path == "/api/ledger":
		var req struct {
			Type       string  `json:"type"`
			Amount     float64 `json:"amount"`
			BookID     int     `json:"bookId"`
			CategoryID int     `json:"categoryId"`
			Date       string  `json:"date"`
			Note       string  `json:"note"`
		}
		json.Unmarshal(raw, &req)
		day := req.Date
		if day == "" {
			day = time.Now().Format("2006-01-02")
		}
		envelope(w, 200, mutation[transactionDTO]{ID: 101, Item: transactionDTO{
			ID: 101, Type: req.Type, Amount: req.Amount, BookID: req.BookID, CategoryID: req.CategoryID,
			Category: nameOf(req.CategoryID), Date: day, Note: req.Note, UserName: "小明",
		}})
	case r.Method == http.MethodGet && r.URL.Path == "/api/ledger":
		budget := 3000.0
		envelope(w, 200, ledgerPageDTO{
			Summary:      summaryDTO{Income: 1200, Expense: 345.5, Balance: 854.5},
			Transactions: []transactionDTO{{ID: 9, Type: "支出", Category: "餐饮", Amount: 38.5, Date: "2026-08-30", Note: "午饭", UserName: "小明"}},
			Total:        1, Page: 1, PageSize: 20, Budget: &budget,
		})
	case r.Method == http.MethodPut && r.URL.Path == "/api/ledger/9":
		envelope(w, 200, mutation[transactionDTO]{ID: 9, Item: transactionDTO{ID: 9, Type: "支出", Category: "交通", Amount: 12, CategoryID: 2}})
	case r.Method == http.MethodDelete && r.URL.Path == "/api/ledger/9":
		envelope(w, 200, nil)
	case r.Method == http.MethodGet && r.URL.Path == "/api/ledger/trend":
		envelope(w, 200, []trendMonthDTO{{Month: "2026-07", Income: 100, Expense: 640}, {Month: "2026-08", Income: 0, Expense: 0}})
	case r.Method == http.MethodGet && r.URL.Path == "/api/ledger/budget":
		envelope(w, 200, budgetDTO{})
	case r.Method == http.MethodPut && r.URL.Path == "/api/ledger/budget":
		value := 5000.0
		envelope(w, 200, budgetDTO{Budget: &value})
	case r.Method == http.MethodGet && r.URL.Path == "/api/todo":
		envelope(w, 200, map[string]any{"todos": []todoDTO{
			{ID: 1, Text: "交房租", Quadrant: "重要不紧急", Due: "本周五", Done: false},
			{ID: 2, Text: "回邮件", Quadrant: "重要紧急", Done: true},
		}})
	case r.Method == http.MethodPost && r.URL.Path == "/api/todo":
		var req map[string]any
		json.Unmarshal(raw, &req)
		quadrant, _ := req["quadrant"].(string)
		envelope(w, 200, mutation[todoDTO]{ID: 31, Item: todoDTO{ID: 31, Text: fmt.Sprint(req["text"]), Quadrant: quadrant, Due: fmt.Sprint(req["due"])}})
	case r.Method == http.MethodPut && r.URL.Path == "/api/todo/1":
		envelope(w, 200, nil)
	case r.Method == http.MethodDelete && r.URL.Path == "/api/todo/1":
		envelope(w, 200, nil)
	case r.Method == http.MethodGet && r.URL.Path == "/api/calendar":
		today := time.Now().Format("2006-01-02")
		envelope(w, 200, map[string]any{"events": []eventDTO{
			{ID: 1, Title: "周会", Date: today, Time: "09:30", Location: "3 号会议室"},
			{ID: 2, Title: "体检", Date: "2026-09-10", Time: "08:00", Done: true},
		}})
	case r.Method == http.MethodPost && r.URL.Path == "/api/calendar":
		envelope(w, 200, mutation[eventDTO]{ID: 41, Item: eventDTO{ID: 41, Title: "新日程", Date: "2026-09-01", Time: "10:00"}})
	case r.Method == http.MethodGet && r.URL.Path == "/api/notes":
		envelope(w, 200, map[string]any{"notes": []noteDTO{
			{ID: 1, Title: "周记", Summary: strings.Repeat("很长的一段笔记内容", 12), Tags: []string{"工作", "复盘"}, UpdatedAt: "2026-08-30T10:00:00"},
			{ID: 2, Title: "购物清单", Summary: "牛奶、鸡蛋", UpdatedAt: "2026-08-29T10:00:00"},
		}})
	case r.Method == http.MethodPost && r.URL.Path == "/api/notes":
		var req map[string]any
		json.Unmarshal(raw, &req)
		envelope(w, 200, mutation[noteDTO]{ID: 51, Item: noteDTO{ID: 51, Title: fmt.Sprint(req["title"]), Summary: fmt.Sprint(req["summary"])}})
	case r.Method == http.MethodGet && r.URL.Path == "/api/habits":
		envelope(w, 200, map[string]any{"habits": []habitDTO{
			{ID: 1, Name: "早起", Streak: 3, Done: true, Week: []bool{true, true, true, false, false, false, false}},
			{ID: 2, Name: "阅读", Streak: 0},
		}})
	case r.Method == http.MethodPost && r.URL.Path == "/api/habits":
		envelope(w, 200, mutation[habitDTO]{ID: 3, Item: habitDTO{ID: 3, Name: "跑步"}})
	case r.Method == http.MethodPut && r.URL.Path == "/api/habits/1":
		envelope(w, 200, mutation[habitDTO]{ID: 1, Item: habitDTO{ID: 1, Name: "早起", Streak: 4, Done: true}})
	case r.Method == http.MethodGet && r.URL.Path == "/api/overview":
		data := overviewDTO{}
		data.MonthExpense = struct {
			Amount float64 `json:"amount"`
			Budget float64 `json:"budget"`
			Trend  float64 `json:"trend"`
		}{Amount: 1250, Budget: 3000, Trend: -12.5}
		data.Todos = []overviewItemDTO{{Text: "交房租", Time: "今天", Tag: "生活"}}
		data.Habits = []habitDTO{{Name: "早起", Done: true}}
		envelope(w, 200, data)
	case r.Method == http.MethodPost && r.URL.Path == "/api/books/join":
		envelope(w, 200, map[string]any{"book": bookDTO{ID: 2, Name: "家庭", Type: "shared"}})
	case r.Method == http.MethodPost && r.URL.Path == "/api/books":
		var req map[string]any
		json.Unmarshal(raw, &req)
		envelope(w, 200, map[string]any{"book": bookDTO{ID: 3, Name: fmt.Sprint(req["name"]), Type: fmt.Sprint(req["type"])}})
	default:
		fail(w, http.StatusNotFound, "接口不存在")
	}
}

func nameOf(id int) string {
	for _, c := range categories {
		if c.ID == id {
			return c.Name
		}
	}
	return "其他"
}
