// 通用请求封装：自动 JSON 解析、错误抛出
export async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    headers: options.body ? { 'Content-Type': 'application/json', ...options.headers } : options.headers,
    ...options,
  })
  if (!res.ok) throw new Error(`请求失败 HTTP ${res.status}`)
  return (await res.json()) as T
}

export const get = <T,>(url: string) => request<T>(url)

export const post = <T,>(url: string, body: unknown) =>
  request<T>(url, { method: 'POST', body: JSON.stringify(body) })

export const put = <T,>(url: string, body: unknown) =>
  request<T>(url, { method: 'PUT', body: JSON.stringify(body) })

export const del = <T,>(url: string) => request<T>(url, { method: 'DELETE' })
