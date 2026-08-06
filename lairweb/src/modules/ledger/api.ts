import { get, post, del } from '../../api/request'

// ---------- 类型 ----------
export interface Transaction {
  id: string
  type: '支出' | '收入'
  category: string
  amount: number
  date: string
  note: string
}

export interface CategoryStat {
  name: string
  amount: number
  percent: number
}

export interface LedgerSummary {
  income: number
  expense: number
  balance: number
}

export interface LedgerData {
  summary: LedgerSummary
  categoryStats: CategoryStat[]
  transactions: Transaction[]
}

export interface CreateTransactionInput {
  type: '支出' | '收入'
  category: string
  amount: number
  date?: string
  note?: string
}

export const CATEGORIES = ['餐饮', '交通', '购物', '居住', '娱乐', '医疗', '学习', '其他']

// ---------- API ----------
export const ledgerApi = {
  list: () => get<LedgerData>('/api/ledger'),
  create: (input: CreateTransactionInput) => post<{ ok: boolean; id: string }>('/api/ledger', input),
  remove: (id: string) => del<{ ok: boolean }>(`/api/ledger/${id}`),
}
