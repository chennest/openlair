package api

import (
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"laircli/internal/config"
)

func serve(t *testing.T, handler http.HandlerFunc) *Client {
	t.Helper()
	server := httptest.NewServer(handler)
	t.Cleanup(server.Close)
	return New(&config.Settings{APIKey: "ol_test_key", BaseURL: server.URL})
}

func respond(body string) http.HandlerFunc {
	return func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		io.WriteString(w, body)
	}
}

func TestGetUnwrapsEnvelopeAndSendsAPIKey(t *testing.T) {
	var seen *http.Request
	client := serve(t, func(w http.ResponseWriter, r *http.Request) {
		seen = r
		io.WriteString(w, `{"code":200,"message":"成功","data":{"id":7,"name":"日常"}}`)
	})
	resp, err := client.Get("/api/books", nil)
	if err != nil {
		t.Fatal(err)
	}
	var book struct {
		ID   int    `json:"id"`
		Name string `json:"name"`
	}
	if err := resp.Into(&book); err != nil {
		t.Fatal(err)
	}
	if book.ID != 7 || book.Name != "日常" {
		t.Fatalf("data 解包不对: %+v", book)
	}
	if got := seen.Header.Get("X-API-Key"); got != "ol_test_key" {
		t.Fatalf("鉴权头不对: %q", got)
	}
	if seen.Header.Get("Content-Type") != "" {
		t.Fatal("GET 不应带 Content-Type")
	}
}

func TestQueryValuesDropEmpties(t *testing.T) {
	var rawQuery string
	client := serve(t, func(w http.ResponseWriter, r *http.Request) {
		rawQuery = r.URL.RawQuery
		io.WriteString(w, `{"code":200,"data":[]}`)
	})
	if _, err := client.Get("/api/ledger", Query{"bookId": "3", "type": "", "keyword": "午饭"}.Values()); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(rawQuery, "type=") {
		t.Fatalf("空值参数应被丢掉: %s", rawQuery)
	}
	if !strings.Contains(rawQuery, "bookId=3") {
		t.Fatalf("bookId 没带上: %s", rawQuery)
	}
	if !strings.Contains(rawQuery, "keyword=%E5%8D%88%E9%A5%AD") {
		t.Fatalf("中文关键词应被 URL 编码后送出: %s", rawQuery)
	}
}

func TestPostSendsJSONBody(t *testing.T) {
	var body string
	var contentType string
	client := serve(t, func(w http.ResponseWriter, r *http.Request) {
		contentType = r.Header.Get("Content-Type")
		raw, _ := io.ReadAll(r.Body)
		body = string(raw)
		io.WriteString(w, `{"code":200,"data":{"id":1}}`)
	})
	if _, err := client.Post("/api/ledger", map[string]any{"type": "支出", "amount": 12.5}); err != nil {
		t.Fatal(err)
	}
	if contentType != "application/json" {
		t.Fatalf("Content-Type: %q", contentType)
	}
	if !strings.Contains(body, `"支出"`) {
		t.Fatalf("中文枚举应原样以 UTF-8 送出: %s", body)
	}
}

func TestEnvelopeErrorBecomesReadableMessage(t *testing.T) {
	client := serve(t, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusForbidden)
		io.WriteString(w, `{"code":403,"message":"你不是该账本成员","data":null}`)
	})
	_, err := client.Get("/api/books/9/members", nil)
	var apiErr *Error
	if !errors.As(err, &apiErr) {
		t.Fatalf("应返回 *Error，实际 %T", err)
	}
	if apiErr.Status != 403 {
		t.Fatalf("状态码丢失: %d", apiErr.Status)
	}
	if apiErr.Error() != "[403] 你不是该账本成员" {
		t.Fatalf("文案不对: %q", apiErr.Error())
	}
}

func TestUnauthorizedHintsAtInit(t *testing.T) {
	client := serve(t, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		io.WriteString(w, `{"code":401,"message":"未登录或登录已过期，请重新登录","data":null}`)
	})
	_, err := client.Get("/api/auth/me", nil)
	if err == nil || !strings.Contains(err.Error(), "lair init") {
		t.Fatalf("401 应提示重新 init: %v", err)
	}
}

func TestUnprocessableDetailIsFlattened(t *testing.T) {
	client := serve(t, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusUnprocessableEntity)
		io.WriteString(w, `{"detail":[{"type":"less_than_equal","loc":["body","amount"],"msg":"Input should be less than or equal to 999999","input":1e9}]}`)
	})
	_, err := client.Post("/api/ledger", map[string]any{"amount": 1e9})
	if err == nil {
		t.Fatal("422 应报错")
	}
	got := err.Error()
	if !strings.HasPrefix(got, "[422] 参数不合法：") {
		t.Fatalf("422 文案前缀不对: %q", got)
	}
	// loc 首项是 body，对用户没意义；应只留字段名。
	if !strings.Contains(got, "amount: Input should be less than or equal to 999999") {
		t.Fatalf("422 detail 压平不对: %q", got)
	}
	if strings.Contains(got, "body.amount") {
		t.Fatalf("loc 前缀没去掉: %q", got)
	}
}

func TestUnparsableBodyStillReportsStatus(t *testing.T) {
	client := serve(t, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusBadGateway)
		io.WriteString(w, "<html>502 Bad Gateway</html>")
	})
	_, err := client.Get("/api/overview", nil)
	if err == nil || !strings.Contains(err.Error(), "[502] 响应无法解析") {
		t.Fatalf("网关 HTML 响应应被兜住: %v", err)
	}
}

func TestUnreachableHostReportedAsConnectionError(t *testing.T) {
	client := New(&config.Settings{APIKey: "ol_x", BaseURL: "http://127.0.0.1:1"})
	_, err := client.Get("/api/books", nil)
	if err == nil || !strings.Contains(err.Error(), "连不上 http://127.0.0.1:1") {
		t.Fatalf("连不上时应给出地址: %v", err)
	}
}

func TestNonEnvelopeResponsePassesThrough(t *testing.T) {
	client := serve(t, respond(`{"plain":true}`))
	resp, err := client.Get("/api/whatever", nil)
	if err != nil {
		t.Fatal(err)
	}
	if string(resp.Data) != `{"plain":true}` {
		t.Fatalf("无 data 字段的响应应原样返回: %s", resp.Data)
	}
}

func TestIntoIgnoresNullData(t *testing.T) {
	client := serve(t, respond(`{"code":200,"message":"成功","data":null}`))
	resp, err := client.Delete("/api/ledger/1")
	if err != nil {
		t.Fatal(err)
	}
	var out map[string]any
	if err := resp.Into(&out); err != nil {
		t.Fatalf("data 为 null 时不该报错: %v", err)
	}
}
