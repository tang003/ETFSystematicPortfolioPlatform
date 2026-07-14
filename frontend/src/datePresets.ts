export type AnalysisPreset = '6m' | '1y' | '3y' | '5y' | 'inception' | 'custom'
export type DataPreset = '1m' | '3m' | AnalysisPreset | '10y'

export const analysisPresetOptions = [
  { label: '半年', value: '6m' },
  { label: '1 年', value: '1y' },
  { label: '3 年', value: '3y' },
  { label: '5 年', value: '5y' },
  { label: '成立以来', value: 'inception' },
  { label: '自定义', value: 'custom' },
]

export const dataPresetOptions = [
  { label: '1 个月', value: '1m' },
  { label: '3 个月', value: '3m' },
  { label: '半年', value: '6m' },
  { label: '1 年', value: '1y' },
  { label: '3 年', value: '3y' },
  { label: '5 年', value: '5y' },
  { label: '成立以来', value: 'inception' },
  { label: '10 年', value: '10y' },
  { label: '自定义', value: 'custom' },
]

export function buildPresetRange(value: DataPreset, endDate = new Date()): [string, string] {
  const end = new Date(endDate)
  const start = new Date(end)
  const monthMap: Partial<Record<DataPreset, number>> = {
    '1m': 1,
    '3m': 3,
    '6m': 6,
    '1y': 12,
    '3y': 36,
    '5y': 60,
    '10y': 120,
  }
  if (value === 'inception') {
    start.setMonth(start.getMonth() - 120)
  } else {
    start.setMonth(start.getMonth() - (monthMap[value] || 12))
  }
  return [formatDate(start), formatDate(end)]
}

export function presetLabel(value: string) {
  const labels: Record<string, string> = {
    '1m': '最近 1 个月',
    '3m': '最近 3 个月',
    '6m': '最近半年',
    '1y': '最近 1 年',
    '3y': '最近 3 年',
    '5y': '最近 5 年',
    '10y': '最近 10 年',
    inception: '成立以来',
    custom: '自定义日期',
  }
  return labels[value] || value
}

export function formatDate(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
