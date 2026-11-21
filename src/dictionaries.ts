import type { Exercise } from './practice'

export const banks = ['traditional', 'simplified'] as const
type Bank = typeof banks[number]
type Difficulty = 'beginner' | 'full'

export interface Settings {
  banks: Bank[]
  difficulty: Difficulty
}

export interface Dictionaries {
  banks: Record<Bank, Record<Difficulty, string[]>>
  codes: CodeTable
}

export type CodeTable = Record<string, string[]>

export const defaultSettings: Settings = { banks: ['traditional'], difficulty: 'beginner' }
export const roundSize = 20
const storageKey = 'typetype.cangjie.settings'

export function readSettings(): Settings {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) ?? 'null')
    const selected = banks.filter((bank) => Array.isArray(saved?.banks) && saved.banks.includes(bank))
    if (selected.length && (saved.difficulty === 'beginner' || saved.difficulty === 'full')) {
      return { banks: selected, difficulty: saved.difficulty }
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

export function drawQuestions(data: Dictionaries, settings: Settings, random = Math.random): Exercise[] {
  const selected = banks.filter((bank) => settings.banks.includes(bank))
  const pools = selected.map((bank) => ({
    bank,
    characters: data.banks[bank][settings.difficulty],
  }))

  if (!pools.length) return []

  const picked = new Map<string, Bank>()
  const quota = roundSize / pools.length
  for (const pool of shuffled(pools, random)) {
    const other = pools.find((candidate) => candidate !== pool)
    const otherCharacters = new Set(other?.characters)
    const candidates = shuffled(pool.characters.filter((character) => !picked.has(character)), random)
    const distinct = other && candidates.find((character) => !otherCharacters.has(character))
    const selection = distinct
      ? [distinct, ...candidates.filter((character) => character !== distinct).slice(0, quota - 1)]
      : candidates.slice(0, quota)
    for (const character of selection) picked.set(character, pool.bank)
  }

  if (picked.size < roundSize) {
    const remaining = new Map<string, Bank>()
    for (const pool of pools) {
      for (const character of pool.characters) {
        if (!picked.has(character)) remaining.set(character, pool.bank)
      }
    }
    for (const [character, bank] of shuffled([...remaining], random).slice(0, roundSize - picked.size)) {
      picked.set(character, bank)
    }
  }

  return shuffled([...picked], random).map(([character, bank]) => {
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
