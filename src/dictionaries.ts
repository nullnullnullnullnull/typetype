import type { Exercise } from './practice'

export const banks = ['traditional', 'simplified'] as const
type Bank = typeof banks[number]
type Difficulty = 'beginner' | 'full'

export interface Settings {
  banks: Bank[]
  mode: 'fixed' | 'endless'
  quantity: number
  difficulty: Difficulty
}

export interface Dictionaries {
  banks: Record<Bank, Record<Difficulty, string[]>>
  codes: CodeTable
}

export type CodeTable = Record<string, string[]>

export const roundSize = 20
export const defaultSettings: Settings = { banks: ['traditional'], difficulty: 'beginner', mode: 'fixed', quantity: roundSize }
const storageKey = 'typetype.cangjie.settings'

export function readSettings(): Settings {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) ?? 'null')
    const selected = banks.filter((bank) => Array.isArray(saved?.banks) && saved.banks.includes(bank))
    if (selected.length && (saved.difficulty === 'beginner' || saved.difficulty === 'full')) {
      return { banks: selected, difficulty: saved.difficulty,
        mode: saved.mode === 'endless' ? 'endless' : 'fixed',
        quantity: Number.isSafeInteger(saved.quantity) && saved.quantity > 0 ? saved.quantity : roundSize,
      }
    }
  } catch {
    // Practice also works when browser storage is unavailable.
  }
  return defaultSettings
}

export function saveSettings(settings: Settings) {
  if (!settings.banks.length) return
  try {
    localStorage.setItem(storageKey, JSON.stringify(settings))
  } catch {
    // The settings remain available for this visit.
  }
}

export function availableCount(data: Dictionaries, settings: Settings) {
  return new Set(settings.banks.flatMap((bank) => data.banks[bank][settings.difficulty])).size
}

export function playable(settings: Settings, count: number) {
  return count > 0 && (settings.mode === 'endless' ||
    (Number.isSafeInteger(settings.quantity) && settings.quantity > 0 && settings.quantity <= count))
}

export function drawQuestions(data: Dictionaries, settings: Settings, random = Math.random, previous?: string): Exercise[] {
  const selected = shuffled(banks.filter(bank => settings.banks.includes(bank)), random)
  if (!selected.length) return []
  const pool = (bank: Bank) => data.banks[bank][settings.difficulty]
  const size = settings.mode === 'endless' ? availableCount(data, settings) : settings.quantity ?? roundSize
  const picked: [string, Bank][] = []
  if (selected.length === 1) {
    for (const char of shuffled(pool(selected[0]), random).slice(0, size)) picked.push([char, selected[0]])
  } else {
    const [a, b] = selected
    const aSet = new Set(pool(a))
    const bSet = new Set(pool(b))
    const shared = shuffled(pool(a).filter(c => bSet.has(c)), random)
    const onlyA = pool(a).filter(c => !bSet.has(c))
    const onlyB = pool(b).filter(c => !aSet.has(c))
    const quotaA = Math.min(aSet.size, Math.max(Math.ceil(size / 2), size - bSet.size))
    const quotaB = size - quotaA
    // Split shared characters once, leaving each bank enough candidates for its quota.
    const split = Math.max(quotaA - onlyA.length,
      Math.min(Math.ceil(shared.length / 2), shared.length - Math.max(0, quotaB - onlyB.length)))
    function pick(bank: Bank, exclusive: string[], common: string[], quota: number) {
      if (quota <= 0) return
      const candidates = shuffled(exclusive, random)
      const first = size > 1 ? candidates.pop() : undefined
      if (first) picked.push([first, bank])
      for (const char of shuffled([...candidates, ...common], random).slice(0, quota - Number(!!first))) {
        picked.push([char, bank])
      }
    }
    pick(a, onlyA, shared.slice(0, split), quotaA)
    pick(b, onlyB, shared.slice(split), quotaB)
  }
  const ordered = shuffled(picked, random)
  if (ordered.length > 1 && ordered[0][0] === previous) {
    const next = 1 + Math.floor(random() * (ordered.length - 1))
    const first = ordered[0]
    ordered[0] = ordered[next]
    ordered[next] = first
  }
  return ordered.map(([character, bank]) => {
    const [code, ...alternateCodes] = data.codes[character]
    return { character, code, alternateCodes, language: bank === 'traditional' ? 'zh-Hant-TW' : 'zh-Hans-CN' }
  })
}

function shuffled<T>(values: readonly T[], random: () => number): T[] {
  const result = [...values]
  for (let index = result.length - 1; index > 0; index--) {
    const swap = Math.floor(random() * (index + 1))
    const value = result[index]
    result[index] = result[swap]
    result[swap] = value
  }
  return result
}
