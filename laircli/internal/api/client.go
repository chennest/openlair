// Package api 是后端 /api 的 HTTP 客户端：X-API-Key 鉴权 + {code,message,data} 信封解包。
//
// 后端的失败形状有两种：业务错误走统一信封（HTTP 状态码 == code），而参数校验 422 是 FastAPI
// 默认的裸 {"detail":[...]}（core/envelope.py 未注册 RequestValidationError handler）。
// 这里把两种形状归一成一个可读的 error 文案。
package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"laircli/internal/config"
)

// Timeout 与 Python 版一致：15s 内没响应就报连不上。
const Timeout = 15 * time.Second

// maxBody 是单次读取的响应体上限，避免异常大响应把内存吃掉。
const maxBody = 8 << 20

// Error 是"已经可以直接打印给用户"的失败：Status 为 0 表示本地/网络层错误。
type Error struct {
	Status int
	Msg    string
}

func (e *Error) Error() string { return e.Msg }

// Client 绑定一份配置；零值不可用，请走 New。
type Client struct {
	BaseURL string
	APIKey  string
	HTTP    *http.Client
	// Debug 非空时，每个请求的概要通过它打到 stderr。
	Debug func(string)
}

func New(settings *config.Settings) *Client {
	return &Client{
		BaseURL: settings.BaseURL,
		APIKey:  settings.APIKey,
		HTTP:    &http.Client{Timeout: Timeout},
	}
}

// Resp 保留信封里的原始 data 字节：--json 模式要按原样输出，不能经过结构体往返丢字段。
type Resp struct {
	Data json.RawMessage
}

// Into 把 data 解到 v；v 传 nil 表示只关心成功与否。
func (r Resp) Into(v any) error {
	if v == nil || len(r.Data) == 0 {
		return nil
	}
	if err := json.Unmarshal(r.Data, v); err != nil {
		return fmt.Errorf("响应解析失败：%v", err)
	}
	return nil
}

func (c *Client) Get(path string, query url.Values) (Resp, error) {
	return c.Do(http.MethodGet, path, query, nil)
}

func (c *Client) Post(path string, body any) (Resp, error) {
	return c.Do(http.MethodPost, path, nil, body)
}

func (c *Client) Put(path string, body any) (Resp, error) {
	return c.Do(http.MethodPut, path, nil, body)
}

func (c *Client) Delete(path string) (Resp, error) {
	return c.Do(http.MethodDelete, path, nil, nil)
}

// Do 发一次请求并解包信封；成功返回 data，失败返回 *Error。
func (c *Client) Do(method, path string, query url.Values, body any) (Resp, error) {
	endpoint := c.BaseURL + path
	if encoded := query.Encode(); encoded != "" {
		endpoint += "?" + encoded
	}

	var payload io.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			return Resp{}, err
		}
		payload = bytes.NewReader(buf)
	}

	req, err := http.NewRequest(method, endpoint, payload)
	if err != nil {
		return Resp{}, &Error{Msg: fmt.Sprintf("请求构造失败：%v", err)}
	}
	req.Header.Set("X-API-Key", c.APIKey)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	res, err := c.HTTP.Do(req)
	if err != nil {
		return Resp{}, &Error{Msg: fmt.Sprintf("连不上 %s：%v", c.BaseURL, err)}
	}
	defer res.Body.Close()

	raw, err := io.ReadAll(io.LimitReader(res.Body, maxBody))
	if err != nil {
		return Resp{}, &Error{Msg: fmt.Sprintf("响应读取中断：%v", err)}
	}
	if c.Debug != nil {
		c.Debug(fmt.Sprintf("%s %s → %d", method, path, res.StatusCode))
	}

	if res.StatusCode >= 200 && res.StatusCode < 300 {
		return Resp{Data: unwrapData(raw)}, nil
	}
	return Resp{}, &Error{Status: res.StatusCode, Msg: errorMessage(res.StatusCode, raw)}
}

// unwrapData 取出信封里的 data；不是标准信封的响应原样返回。
func unwrapData(raw []byte) json.RawMessage {
	var envelope map[string]json.RawMessage
	if json.Unmarshal(raw, &envelope) != nil {
		return json.RawMessage(raw)
	}
	data, ok := envelope["data"]
	if !ok {
		return json.RawMessage(raw)
	}
	return data
}

func errorMessage(status int, raw []byte) string {
	var payload map[string]json.RawMessage
	if json.Unmarshal(raw, &payload) != nil {
		return fmt.Sprintf("[%d] 响应无法解析", status)
	}
	var message string
	if json.Unmarshal(payload["message"], &message) == nil && message != "" {
		suffix := ""
		if status == http.StatusUnauthorized {
			suffix = "（API Key 无效或已被撤销：lair config 核对，或重新 lair init）"
		}
		return fmt.Sprintf("[%d] %s%s", status, message, suffix)
	}
	// 422：FastAPI 裸 detail 数组，逐项压成一行。
	var details []json.RawMessage
	if json.Unmarshal(payload["detail"], &details) == nil && len(details) > 0 {
		parts := make([]string, 0, len(details))
		for _, item := range details {
			parts = append(parts, detailText(item))
		}
		return fmt.Sprintf("[%d] 参数不合法：%s", status, strings.Join(parts, "；"))
	}
	var detail string
	if json.Unmarshal(payload["detail"], &detail) == nil && detail != "" {
		return fmt.Sprintf("[%d] %s", status, detail)
	}
	return fmt.Sprintf("[%d] 响应无法解析", status)
}

// detailText 把 {"loc":["body","amount"],"msg":"..."} 压成 "amount: ..."；
// loc 首项是请求体位置（body/query/path），对用户没意义，跳过。
func detailText(raw json.RawMessage) string {
	var item struct {
		Loc  []any  `json:"loc"`
		Msg  string `json:"msg"`
		Type string `json:"type"`
	}
	if json.Unmarshal(raw, &item) != nil {
		return string(raw)
	}
	loc := make([]string, 0, len(item.Loc))
	for _, part := range item.Loc[min(1, len(item.Loc)):] {
		switch v := part.(type) {
		case float64:
			loc = append(loc, strconv.Itoa(int(v)))
		default:
			loc = append(loc, fmt.Sprint(v))
		}
	}
	text := item.Msg
	if text == "" {
		text = item.Type
	}
	if text == "" {
		text = "字段不合法"
	}
	if len(loc) == 0 {
		return text
	}
	return strings.Join(loc, ".") + ": " + text
}

// Query 是构造可选查询参数的帮手：空串一律丢弃，语义对齐 Python 版的 None 过滤。
type Query map[string]string

func (q Query) Values() url.Values {
	out := url.Values{}
	for key, value := range q {
		if value != "" {
			out.Set(key, value)
		}
	}
	return out
}
