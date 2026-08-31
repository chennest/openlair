// Package render 是输出层：--json 时 stdout 只留纯 JSON，人类提示一律让路。
//
// 表格里全是中文，所以列宽必须按显示宽度（东亚字符占 2 列）算，否则对不齐。
package render

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"strings"
)

const (
	ansiReset  = "\x1b[0m"
	ansiDim    = "\x1b[2m"
	ansiGreen  = "\x1b[32m"
	ansiYellow = "\x1b[33m"
	ansiRed    = "\x1b[31m"
)

// Align 是列对齐方式。
type Align int

const (
	Left Align = iota
	Right
	Center
)

// Col 是表头的一列。
type Col struct {
	Title string
	Align Align
}

// R 绑定输出流。Quiet 表示 JSON 模式：抑制一切人类提示。
type R struct {
	Out   io.Writer
	Err   io.Writer
	Quiet bool
	Color bool
}

func New(out, errw io.Writer, quiet, color bool) *R {
	return &R{Out: out, Err: errw, Quiet: quiet, Color: color}
}

// Data 原样缩进输出信封里的 data 字节，保持服务端字段与中文不被改写。
func (r *R) Data(raw []byte) error {
	var buf bytes.Buffer
	if err := json.Indent(&buf, raw, "", "  "); err != nil {
		_, werr := fmt.Fprintln(r.Out, string(raw))
		return werr
	}
	buf.WriteByte('\n')
	_, err := r.Out.Write(buf.Bytes())
	return err
}

// JSON 输出程序内构造的对象（没有服务端原始字节时用它）。
func (r *R) JSON(v any) error {
	buf := &bytes.Buffer{}
	enc := json.NewEncoder(buf)
	enc.SetIndent("", "  ")
	enc.SetEscapeHTML(false)
	if err := enc.Encode(v); err != nil {
		return err
	}
	_, err := io.WriteString(r.Out, strings.TrimSuffix(buf.String(), "\n")+"\n")
	return err
}

func (r *R) Log(message string)           { fmt.Fprintln(r.Out, message) }
func (r *R) Logf(format string, a ...any) { fmt.Fprintf(r.Out, format+"\n", a...) }
func (r *R) OK(message string)            { fmt.Fprintln(r.Out, r.paint(message, ansiGreen)) }
func (r *R) Hint(message string) {
	if !r.Quiet {
		fmt.Fprintln(r.Out, r.paint(message, ansiDim))
	}
}
func (r *R) Warn(message string) { fmt.Fprintln(r.Err, r.paint(message, ansiYellow)) }
func (r *R) Fail(message string) { fmt.Fprintln(r.Err, r.paint(message, ansiRed)) }
func (r *R) Debug(message string) {
	fmt.Fprintln(r.Err, r.paint("» "+message, ansiDim))
}

func (r *R) paint(message, color string) string {
	if !r.Color {
		return message
	}
	return color + message + ansiReset
}

// Table 按显示宽度对齐输出网格；空数据打一行占位提示。
func (r *R) Table(cols []Col, rows [][]string) {
	if len(rows) == 0 {
		r.Log(r.paint("（空）", ansiDim))
		return
	}
	widths := make([]int, len(cols))
	for i, col := range cols {
		widths[i] = Width(col.Title)
	}
	for _, row := range rows {
		for i, cell := range row {
			if i < len(widths) && Width(cell) > widths[i] {
				widths[i] = Width(cell)
			}
		}
	}
	r.Log(r.paint(renderRow(cols, widths, titles(cols), false), ansiDim))
	r.Log(strings.Repeat("─", totalWidth(widths)))
	for _, row := range rows {
		r.Log(renderRow(cols, widths, row, true))
	}
}

func titles(cols []Col) []string {
	out := make([]string, len(cols))
	for i, col := range cols {
		out[i] = col.Title
	}
	return out
}

func totalWidth(widths []int) int {
	total := 0
	for _, w := range widths {
		total += w
	}
	return total + 2*(len(widths)-1)
}

// renderRow 拼一行；dataRow 时空单元格补 "-"，表头里的空标题保持留白。
func renderRow(cols []Col, widths []int, cells []string, dataRow bool) string {
	parts := make([]string, 0, len(cols))
	for i, col := range cols {
		cell := ""
		if i < len(cells) {
			cell = cells[i]
		}
		if cell == "" && dataRow {
			cell = "-"
		}
		parts = append(parts, pad(cell, widths[i], col.Align))
	}
	return strings.TrimRight(strings.Join(parts, "  "), " ")
}

func pad(cell string, width int, align Align) string {
	gap := width - Width(cell)
	if gap <= 0 {
		return cell
	}
	switch align {
	case Right:
		return strings.Repeat(" ", gap) + cell
	case Center:
		left := gap / 2
		return strings.Repeat(" ", left) + cell + strings.Repeat(" ", gap-left)
	default:
		return cell + strings.Repeat(" ", gap)
	}
}

// Width 返回字符串在终端里占的列数：东亚全角/宽字符算 2，控制字符算 0。
func Width(s string) int {
	total := 0
	for _, r := range s {
		total += runeWidth(r)
	}
	return total
}

func runeWidth(r rune) int {
	switch {
	case r < 0x20 || (r >= 0x7f && r < 0xa0):
		return 0
	case inRanges(r, wideRanges):
		return 2
	default:
		return 1
	}
}

type runeRange struct{ lo, hi rune }

// wideRanges 是 Unicode EastAsianWidth 里 W/F 的主要区段（含常用 emoji 区）。
var wideRanges = []runeRange{
	{0x1100, 0x115f}, {0x2e80, 0x303e}, {0x3041, 0x33ff}, {0x3400, 0x4dbf},
	{0x4e00, 0x9fff}, {0xa000, 0xa4cf}, {0xac00, 0xd7a3}, {0xf900, 0xfaff},
	{0xfe10, 0xfe19}, {0xfe30, 0xfe6f}, {0xff00, 0xff60}, {0xffe0, 0xffe6},
	{0x1f300, 0x1f64f}, {0x1f900, 0x1f9ff}, {0x20000, 0x3fffd},
}

func inRanges(r rune, ranges []runeRange) bool {
	for _, span := range ranges {
		if r >= span.lo && r <= span.hi {
			return true
		}
	}
	return false
}
