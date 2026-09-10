package commands

// 后端 DTO 的 Go 映射：字段名与 mock 层逐一对齐（camelCase），未列出的字段解码时忽略。

type transactionDTO struct {
	ID         int     `json:"id"`
	Type       string  `json:"type"`
	CategoryID int     `json:"categoryId"`
	Category   string  `json:"category"`
	BookID     int     `json:"bookId"`
	Amount     float64 `json:"amount"`
	Date       string  `json:"date"`
	Note       string  `json:"note"`
	UserName   string  `json:"userName"`
}

type summaryDTO struct {
	Income  float64 `json:"income"`
	Expense float64 `json:"expense"`
	Balance float64 `json:"balance"`
}

type ledgerPageDTO struct {
	Summary      summaryDTO       `json:"summary"`
	Transactions []transactionDTO `json:"transactions"`
	Total        int              `json:"total"`
	Page         int              `json:"page"`
	PageSize     int              `json:"pageSize"`
	Budget       *float64         `json:"budget"`
}

type trendMonthDTO struct {
	Month   string  `json:"month"`
	Income  float64 `json:"income"`
	Expense float64 `json:"expense"`
}

type budgetDTO struct {
	Budget *float64 `json:"budget"`
}

type categoryDTO struct {
	ID        int    `json:"id"`
	Name      string `json:"name"`
	Type      string `json:"type"`
	IsDefault bool   `json:"isDefault"`
	UserID    *int   `json:"userId"` // nil = 系统预置；非空 = 用户自定义（该用户可改删）
}

type memberDTO struct {
	Role string  `json:"role"`
	User userDTO `json:"user"`
}

type userDTO struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
}

type bookDTO struct {
	ID      int         `json:"id"`
	Name    string      `json:"name"`
	Type    string      `json:"type"`
	Members []memberDTO `json:"members"`
}

type todoDTO struct {
	ID       int    `json:"id"`
	Text     string `json:"text"`
	Quadrant string `json:"quadrant"`
	Due      string `json:"due"`
	Done     bool   `json:"done"`
}

type eventDTO struct {
	ID       int    `json:"id"`
	Title    string `json:"title"`
	Date     string `json:"date"`
	Time     string `json:"time"`
	Location string `json:"location"`
	Done     bool   `json:"done"`
}

type noteDTO struct {
	ID        int      `json:"id"`
	Title     string   `json:"title"`
	Summary   string   `json:"summary"`
	Tags      []string `json:"tags"`
	UpdatedAt string   `json:"updatedAt"`
}

type habitDTO struct {
	ID     int    `json:"id"`
	Name   string `json:"name"`
	Streak int    `json:"streak"`
	Done   bool   `json:"done"`
	Week   []bool `json:"week"`
}

type overviewDTO struct {
	MonthExpense struct {
		Amount float64 `json:"amount"`
		Budget float64 `json:"budget"`
		Trend  float64 `json:"trend"`
	} `json:"monthExpense"`
	RecentLedger []transactionDTO  `json:"recentLedger"`
	Todos        []overviewItemDTO `json:"todos"`
	Upcoming     []overviewItemDTO `json:"upcoming"`
	Habits       []habitDTO        `json:"habits"`
}

type overviewItemDTO struct {
	Text string `json:"text"`
	Time string `json:"time"`
	Tag  string `json:"tag"`
	Date string `json:"date"`
	Name string `json:"name"`
	Done bool   `json:"done"`
}

type meDTO struct {
	ID        int    `json:"id"`
	Name      string `json:"name"`
	Email     string `json:"email"`
	CreatedAt string `json:"createdAt"`
}

// mutation 覆盖各写接口的 {id, item} 返回形状。
type mutation[T any] struct {
	ID   int `json:"id"`
	Item T   `json:"item"`
}
