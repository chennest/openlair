// Package cli 是一层极小的子命令 + flag 解析：够撑起中文帮助与命令树，不引第三方依赖。
//
// 约定：长选项 --name、短选项 -x、两者都支持 --name=值；根命令上的全局选项可以在任意位置出现；
// 单个 "-" 以及作为选项值出现的 token 不参与选项识别（所以 `-t -` 能把 "-" 当成支出别名）。
package cli

import (
	"fmt"
	"io"
	"strconv"
	"strings"

	"laircli/internal/render"
)

// Kind 决定选项要不要吃掉下一个 token。
type Kind int

const (
	String Kind = iota
	Bool
	Int
	Float
	Strings
)

func (k Kind) placeholder() string {
	switch k {
	case Bool:
		return ""
	case Int:
		return "整数"
	case Float:
		return "数字"
	default:
		return "字符串"
	}
}

// Flag 是一个选项定义。Default 只在用户没给值时生效。
type Flag struct {
	Name    string
	Short   string
	Usage   string
	Kind    Kind
	Default any
}

// Arg 是位置参数定义；Variadic 表示吃掉剩下的全部 token。
type Arg struct {
	Name     string
	Optional bool
	Variadic bool
}

// Command 是命令树上的一环：有 Sub 没有 Run 时是分组，反之是叶子。
type Command struct {
	Name  string
	Short string
	Long  string
	Args  []Arg
	Flags []*Flag
	Sub   []*Command
	Run   func(*Context, *Inv) error

	// Prepare 只有根命令会用：全局选项解析完、分发叶子命令前，把运行期对象填进 Context.App。
	Prepare func(*Context, *Inv) error
}

// Context 是一次执行的输入输出。
type Context struct {
	Out io.Writer
	Err io.Writer
	In  io.Reader
	App any
}

// UsageError 占退出码 2，与"接口调用失败"区分。
type UsageError struct{ Msg string }

func (e *UsageError) Error() string { return e.Msg }

func Usagef(format string, a ...any) *UsageError {
	return &UsageError{Msg: fmt.Sprintf(format, a...)}
}

// Inv 是一次命令调用的解析结果。
type Inv struct {
	cmd  *Command
	Args []string
	vals map[string]stored
}

type stored struct {
	s    string
	b    bool
	i    int64
	f    float64
	list []string
	seen bool
}

// Execute 解析并执行 args；返回 nil 表示已处理完（含 --help），返回 *UsageError 表示用法错误。
func Execute(root *Command, args []string, ctx *Context) error {
	cur := root
	chain := []*Command{root}
	path := []string{root.Name}
	in := &Inv{cmd: cur, vals: map[string]stored{}}
	var positional []string
	showHelp := false

	for len(args) > 0 {
		tok := args[0]
		args = args[1:]
		switch {
		case tok == "--":
			positional = append(positional, args...)
			args = nil
		case tok == "-h" || tok == "--help":
			showHelp = true
		case strings.HasPrefix(tok, "--"):
			name, raw, hasRaw := splitValue(tok[2:])
			f := lookupLong(chain, name)
			if f == nil {
				return Usagef("未知选项 --%s（%s --help 看可用选项）", name, strings.Join(path, " "))
			}
			value, rest, err := takeValue(f, "--"+name, raw, hasRaw, args)
			if err != nil {
				return err
			}
			args = rest
			in.store(f, value)
		case len(tok) > 1 && tok[0] == '-':
			name, raw, hasRaw := splitValue(tok[1:])
			f := lookupShort(chain, name)
			if f == nil {
				return Usagef("未知选项 -%s（%s --help 看可用选项）", name, strings.Join(path, " "))
			}
			value, rest, err := takeValue(f, "-"+name, raw, hasRaw, args)
			if err != nil {
				return err
			}
			args = rest
			in.store(f, value)
		default:
			if len(positional) == 0 {
				if sub := find(cur, tok); sub != nil {
					cur = sub
					chain = append(chain, sub)
					path = append(path, tok)
					in.cmd = sub
					continue
				}
			}
			positional = append(positional, tok)
		}
	}

	if showHelp {
		fmt.Fprint(ctx.Out, help(root, cur, path))
		return nil
	}

	in.Args = positional
	if cur.Run == nil {
		if len(positional) > 0 {
			return Usagef("未知子命令：%s\n%s 可用：%s", positional[0], strings.Join(path, " "), strings.Join(subNames(cur), "、"))
		}
		fmt.Fprint(ctx.Out, help(root, cur, path))
		return nil
	}
	seedDefaults(chain, in)
	if err := checkArgs(cur, path, positional); err != nil {
		return err
	}
	if root.Prepare != nil {
		if err := root.Prepare(ctx, in); err != nil {
			return err
		}
	}
	return cur.Run(ctx, in)
}

// Str 读字符串选项；未给时返回 Default（再退化为空串）。
func (in *Inv) Str(name string) string {
	if v, ok := in.vals[name]; ok {
		return v.s
	}
	return ""
}

func (in *Inv) Bool(name string) bool {
	v, ok := in.vals[name]
	return ok && v.b
}

func (in *Inv) Int(name string) int64 {
	v, ok := in.vals[name]
	if !ok {
		return 0
	}
	return v.i
}

func (in *Inv) Float(name string) float64 {
	v, ok := in.vals[name]
	if !ok {
		return 0
	}
	return v.f
}

func (in *Inv) List(name string) []string {
	v, ok := in.vals[name]
	if !ok {
		return nil
	}
	return v.list
}

// Has 表示用户是否显式给了这个选项（区分"没给"与"给了空值"）。
func (in *Inv) Has(name string) bool {
	v, ok := in.vals[name]
	return ok && v.seen
}

// OptInt 给了就返回指针，未给返回 nil——用于"覆盖默认"类选项。
func (in *Inv) OptInt(name string) *int {
	if !in.Has(name) {
		return nil
	}
	value := int(in.Int(name))
	return &value
}

// OptFloat 同 OptInt，用于金额。
func (in *Inv) OptFloat(name string) *float64 {
	if !in.Has(name) {
		return nil
	}
	value := in.Float(name)
	return &value
}

// Arg 取第 i 个位置参数，越界返回空串。
func (in *Inv) Arg(i int) string {
	if i < 0 || i >= len(in.Args) {
		return ""
	}
	return in.Args[i]
}

// Rest 取第 i 个之后的全部位置参数（配合 Variadic）。
func (in *Inv) Rest(i int) []string {
	if i >= len(in.Args) {
		return nil
	}
	return in.Args[i:]
}

func (in *Inv) store(f *Flag, raw string) {
	next := stored{seen: true}
	if current, existed := in.vals[f.Name]; existed {
		next = current
		next.seen = true
	}
	switch f.Kind {
	case Bool:
		next.b = raw == "true"
	case Int:
		next.i, _ = strconv.ParseInt(raw, 10, 64)
	case Float:
		next.f, _ = strconv.ParseFloat(raw, 64)
	case Strings:
		next.list = append(next.list, raw)
	default:
		next.s = raw
	}
	in.vals[f.Name] = next
}

// lookupLong 只按 --name 匹配；lookupShort 只按 -x 匹配。分开才不会让 --v 命中 -v。
func lookupLong(chain []*Command, name string) *Flag  { return lookup(chain, name, false) }
func lookupShort(chain []*Command, name string) *Flag { return lookup(chain, name, true) }

func lookup(chain []*Command, name string, short bool) *Flag {
	for i := len(chain) - 1; i >= 0; i-- {
		for _, f := range chain[i].Flags {
			if short {
				if f.Short == name {
					return f
				}
				continue
			}
			if f.Name == name {
				return f
			}
		}
	}
	return nil
}

func find(cur *Command, name string) *Command {
	for _, sub := range cur.Sub {
		if sub.Name == name {
			return sub
		}
	}
	return nil
}

func subNames(cur *Command) []string {
	names := make([]string, 0, len(cur.Sub))
	for _, sub := range cur.Sub {
		names = append(names, sub.Name)
	}
	return names
}

// takeValue 负责"这个选项要不要下一个 token"，返回取值与剩余 args。
func takeValue(f *Flag, label, raw string, hasRaw bool, args []string) (string, []string, error) {
	if f.Kind == Bool {
		if !hasRaw {
			return "true", args, nil
		}
		switch strings.ToLower(raw) {
		case "1", "true", "yes":
			return "true", args, nil
		case "0", "false", "no":
			return "false", args, nil
		}
		return "", args, Usagef("%s 是开关选项，不接受 %q", label, raw)
	}
	if hasRaw {
		return raw, args, nil
	}
	if len(args) == 0 {
		return "", args, Usagef("%s 需要一个%s", label, f.Kind.placeholder())
	}
	return args[0], args[1:], nil
}

func splitValue(token string) (name, raw string, hasRaw bool) {
	if i := strings.IndexByte(token, '='); i >= 0 {
		return token[:i], token[i+1:], true
	}
	return token, "", false
}

func seedDefaults(chain []*Command, in *Inv) {
	for _, cmd := range chain {
		for _, f := range cmd.Flags {
			if _, ok := in.vals[f.Name]; ok || f.Default == nil {
				continue
			}
			in.vals[f.Name] = stored{s: toString(f.Default), b: toBool(f.Default), i: toInt(f.Default), f: toFloat(f.Default)}
		}
	}
}

func toString(v any) string {
	s, _ := v.(string)
	return s
}

func toBool(v any) bool {
	b, _ := v.(bool)
	return b
}

func toInt(v any) int64 {
	switch n := v.(type) {
	case int:
		return int64(n)
	case int64:
		return n
	}
	return 0
}

func toFloat(v any) float64 {
	switch n := v.(type) {
	case float64:
		return n
	case int:
		return float64(n)
	}
	return 0
}

func checkArgs(cur *Command, path []string, positional []string) error {
	required, maxArgs, variadic := 0, 0, false
	for _, a := range cur.Args {
		maxArgs++
		if !a.Optional && !a.Variadic {
			required++
		}
		if a.Variadic {
			variadic = true
		}
	}
	usage := usageLine(cur, path)
	if len(positional) < required {
		return Usagef("缺少参数 <%s>（用法：%s）", cur.Args[len(positional)].Name, usage)
	}
	if !variadic && len(positional) > maxArgs {
		return Usagef("多余参数：%s（用法：%s）", strings.Join(positional[maxArgs:], " "), usage)
	}
	return nil
}

func usageLine(cur *Command, path []string) string {
	parts := append(append([]string{}, path...), argumentPattern(cur)...)
	return strings.Join(parts, " ")
}

func argumentPattern(cur *Command) []string {
	parts := make([]string, 0, len(cur.Args)+1)
	for _, a := range cur.Args {
		switch {
		case a.Variadic:
			parts = append(parts, "<"+a.Name+"...>")
		case a.Optional:
			parts = append(parts, "["+a.Name+"]")
		default:
			parts = append(parts, "<"+a.Name+">")
		}
	}
	if len(cur.Sub) == 0 && len(parts) == 0 {
		parts = append(parts, "[选项]")
	}
	return parts
}

// help 生成单个命令的完整帮助文本；全局选项单列一节，避免每个命令重复。
func help(root, cur *Command, path []string) string {
	var b strings.Builder
	b.WriteString("用法:\n  " + usageLine(cur, path) + "\n")
	if len(cur.Sub) > 0 {
		b.WriteString("  " + strings.Join(path, " ") + " <子命令> --help\n")
	}
	b.WriteString("\n")

	switch {
	case cur.Long != "":
		b.WriteString(strings.TrimRight(cur.Long, "\n") + "\n\n")
	case cur.Short != "":
		b.WriteString(cur.Short + "\n\n")
	}

	if len(cur.Sub) > 0 {
		b.WriteString("子命令:\n")
		rows := make([][2]string, 0, len(cur.Sub))
		for _, sub := range cur.Sub {
			rows = append(rows, [2]string{"  " + sub.Name, sub.Short})
		}
		b.WriteString(writeColumns(rows))
		b.WriteString("\n")
	}

	rows := make([][2]string, 0, len(cur.Flags)+1)
	for _, f := range cur.Flags {
		rows = append(rows, [2]string{flagPattern(f), f.Usage})
	}
	rows = append(rows, [2]string{"      --help", "看这份帮助"})
	b.WriteString("选项:\n" + writeColumns(rows) + "\n")

	if root.Name != cur.Name && len(root.Flags) > 0 {
		globalRows := make([][2]string, 0, len(root.Flags))
		for _, f := range root.Flags {
			globalRows = append(globalRows, [2]string{flagPattern(f), f.Usage})
		}
		b.WriteString("全局选项:\n" + writeColumns(globalRows) + "\n")
	}

	if len(cur.Sub) > 0 {
		b.WriteString("用 \"" + strings.Join(path, " ") + " <子命令> --help\" 看单条命令的选项。\n")
	}
	return b.String()
}

func flagPattern(f *Flag) string {
	left := "  "
	if f.Short != "" {
		left += "-" + f.Short + ", "
	} else {
		left += "    "
	}
	text := left + "--" + f.Name
	if p := f.Kind.placeholder(); p != "" {
		text += " " + p
	}
	return text
}

// writeColumns 按显示宽度对齐两列：占位符是中文，按字节数算会把列错开。
func writeColumns(rows [][2]string) string {
	width := 0
	for _, row := range rows {
		if n := render.Width(row[0]); n > width {
			width = n
		}
	}
	var b strings.Builder
	for _, row := range rows {
		b.WriteString(row[0] + strings.Repeat(" ", width-render.Width(row[0])+2) + row[1] + "\n")
	}
	return strings.TrimRight(b.String(), " \n") + "\n"
}
