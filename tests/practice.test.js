import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { availableCount, drawQuestions, readSettings, roundSize, saveSettings } from '../src/dictionaries.ts'
import { practiceReducer, roundStats, startRound } from '../src/practice.ts'

const characters = (start, length) => Array.from(
  { length }, (_, index) => String.fromCodePoint(start + index),
)
const shared = characters(0x4e00, 25)
const traditional = characters(0x5000, 25)
const simplified = characters(0x5200, 25)
const fixture = {
  banks: {
    traditional: { beginner: [...shared, ...traditional], full: [...shared, ...traditional, '語'] },
    simplified: { beginner: [...shared, ...simplified], full: [...shared, ...simplified, '语'] },
  },
  codes: Object.fromEntries([...shared, ...traditional, ...simplified, '語', '语'].map(
    (character) => [character, ['ABC', 'DEF']],
  )),
}

test('every bank and difficulty combination generates a unique 20-question round', () => {
  for (const difficulty of ['beginner', 'full']) {
    for (const banks of [['traditional'], ['simplified'], ['traditional', 'simplified']]) {
      const settings = { banks, difficulty }
      const eligible = new Set(banks.flatMap((bank) => fixture.banks[bank][difficulty]))
      assert.equal(availableCount(fixture, settings), eligible.size)
      for (const random of [() => 0, () => 0.99]) {
        const round = drawQuestions(fixture, settings, random)
        assert.equal(round.length, roundSize)
        assert.equal(new Set(round.map(({ character }) => character)).size, roundSize)
        assert.ok(round.every(({ character }) => eligible.has(character)))
        if (banks.length === 2) {
          assert.equal(round.filter(({ language }) => language === 'zh-Hant-TW').length, 10)
          assert.equal(round.filter(({ language }) => language === 'zh-Hans-CN').length, 10)
          assert.ok(round.some(({ character }) => traditional.includes(character) || character === '語'))
          assert.ok(round.some(({ character }) => simplified.includes(character) || character === '语'))
        }
      }
    }
  }
})

test('mixed rounds fill a short quota from the other bank without duplicates', () => {
  const data = {
    ...fixture,
    banks: { ...fixture.banks, traditional: { ...fixture.banks.traditional, beginner: shared.slice(0, 3) } },
  }
  const result = drawQuestions(data, { banks: ['traditional', 'simplified'], difficulty: 'beginner' }, () => 0.99)
  assert.equal(new Set(result.map(({ character }) => character)).size, 20)
  assert.equal(result.filter(({ language }) => language === 'zh-Hant-TW').length, 3)
  assert.deepEqual(drawQuestions(data, { banks: [], difficulty: 'beginner' }), [])
})

test('an incorrect edit waits for confirmation and a correct alternate code advances automatically', () => {
  const exercises = [{ character: '次', code: 'MMNO', alternateCodes: ['IMNO'] }]
  const round = startRound('characters', exercises, 5)
  const edited = practiceReducer(round, { type: 'edit', value: 'im' })
  assert.equal(edited.entry, 'IM')
  assert.equal(edited.wrongEntries, 0)
  assert.equal(roundStats(edited).completed, 0)
  const wrong = practiceReducer(edited, { type: 'submit' })
  assert.equal(wrong.wrongEntries, 1)
  assert.equal(wrong.entry, '')
  const solved = practiceReducer(wrong, { type: 'edit', value: 'imno' })
  assert.equal(solved.exercises, exercises)
  assert.equal(solved.acceptedCode, 'IMNO')
  assert.deepEqual(roundStats(solved), { completed: 1, solved: 1, skipped: 0, accuracy: 0 })
})

test('screen keys automatically advance one question after a complete code', () => {
  const round = startRound('characters', [
    { character: '明', code: 'AB' },
    { character: '林', code: 'DD' },
  ], 5)
  const firstKey = practiceReducer(round, { type: 'append', key: 'A' })
  assert.equal(roundStats(firstKey).completed, 0)
  const solved = practiceReducer(firstKey, { type: 'append', key: 'B' })
  assert.equal(solved.entry, '')
  assert.deepEqual(roundStats(solved), { completed: 1, solved: 1, skipped: 0, accuracy: 100 })
  assert.equal(practiceReducer(solved, { type: 'submit' }), solved)
})

test('every overlapping answer in the dictionary supports manual short codes and automatic long codes', () => {
  const { codes } = JSON.parse(readFileSync(new URL('../public/dictionaries.json', import.meta.url), 'utf8'))
  const pairs = Object.entries(codes).flatMap(([character, answers]) =>
    answers.flatMap((short) => answers
      .filter((long) => long !== short && long.startsWith(short))
      .map((long) => ({ character, answers, short, long }))),
  )
  assert.ok(pairs.length > 0)
  for (const { character, answers: [code, ...alternateCodes], short, long } of pairs) {
    const round = startRound('characters', [{ character, code, alternateCodes }], 5)
    const waiting = practiceReducer(round, { type: 'edit', value: short })
    assert.equal(waiting.entry, short)
    assert.equal(roundStats(waiting).completed, 0)
    assert.equal(practiceReducer(waiting, { type: 'submit' }).acceptedCode, short)
    const solved = practiceReducer(waiting, { type: 'edit', value: long })
    assert.equal(solved.acceptedCode, long)
    assert.equal(roundStats(solved).completed, 1)
  }
})

test('settings retain the last playable selection when the checkboxes are cleared', () => {
  const storage = new Map()
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  })
  const selection = { banks: ['traditional', 'simplified'], difficulty: 'full' }
  try {
    saveSettings(selection)
    saveSettings({ banks: [], difficulty: 'beginner' })
    assert.deepEqual(readSettings(), { ...selection, quantity: 20, mode: 'fixed' })
  } finally {
    delete globalThis.localStorage
  }
})

test('the published dictionary supports all bank and difficulty combinations', () => {
  const data = JSON.parse(readFileSync(new URL('../public/dictionaries.json', import.meta.url), 'utf8'))
  assert.equal(data.banks.traditional.full.length, 4808)
  assert.equal(data.banks.simplified.full.length, 3500)

  for (const bank of Object.values(data.banks)) {
    assert.equal(new Set(bank.full).size, bank.full.length)
    assert.ok(bank.beginner.length >= roundSize)
    const full = new Set(bank.full)
    assert.ok(bank.beginner.every((character) => full.has(character)))
    for (const character of full) {
      const codes = data.codes[character]
      assert.ok(codes?.length && codes.every((code) => /^[A-Y]{1,5}$/.test(code)))
    }
  }

  assert.deepEqual(data.codes['次'], ['IMNO', 'MMNO'])
})

test('the Tiger table covers the same banks and supports all six practice settings', () => {
  const { banks } = JSON.parse(readFileSync(new URL('../public/dictionaries.json', import.meta.url), 'utf8'))
  const codes = JSON.parse(readFileSync(new URL('../public/tiger-codes.json', import.meta.url), 'utf8'))
  const characters = new Set(Object.values(banks).flatMap((bank) => bank.full))
  assert.equal(Object.keys(codes).length, characters.size)
  for (const character of characters) {
    assert.ok(codes[character]?.length)
    assert.ok(codes[character].every((code) => /^[A-Z]{1,4}$/.test(code)))
  }
  for (const difficulty of ['beginner', 'full']) {
    for (const selected of [['traditional'], ['simplified'], ['traditional', 'simplified']]) {
      const questions = drawQuestions({ banks, codes }, { banks: selected, difficulty })
      const eligible = new Set(selected.flatMap((bank) => banks[bank][difficulty]))
      assert.equal(questions.length, 20)
      assert.equal(new Set(questions.map(({ character }) => character)).size, 20)
      assert.ok(questions.every(({ character, code }) => eligible.has(character) && codes[character].includes(code)))
      if (selected.length === 2) {
        assert.equal(questions.filter(({ language }) => language === 'zh-Hant-TW').length, 10)
      }
    }
  }
})

test('Tiger short codes wait for confirmation and four-letter codes advance automatically', () => {
  const codes = JSON.parse(readFileSync(new URL('../public/tiger-codes.json', import.meta.url), 'utf8'))
  const [code, ...alternateCodes] = codes['国']
  assert.deepEqual([code, ...alternateCodes], ['RNID', 'RNI', 'RN'])
  const round = startRound('characters', [{ character: '国', code, alternateCodes }], 4)
  const waiting = [...'RN'].reduce((state, key) => practiceReducer(state, { type: 'append', key }), round)
  assert.equal(waiting.entry, 'RN')
  assert.equal(roundStats(waiting).completed, 0)
  assert.equal(practiceReducer(waiting, { type: 'submit' }).acceptedCode, 'RN')
  const long = practiceReducer(waiting, { type: 'edit', value: 'rnid' })
  assert.equal(long.acceptedCode, 'RNID')
  assert.equal(roundStats(long).completed, 1)
  const tooLong = practiceReducer(round, { type: 'edit', value: 'rnidx' })
  assert.equal(tooLong.entry, 'RNID')
  assert.equal(roundStats(tooLong).completed, 0)
})


test('custom lengths and endless cycles cover the union without duplicate or adjacent repeats', () => {
  const selection = { banks: ['traditional', 'simplified'], difficulty: 'beginner' }
  for (const quantity of [1, 3, 75]) {
    const questions = drawQuestions(fixture, { ...selection, mode: 'fixed', quantity })
    assert.equal(questions.length, quantity)
    assert.equal(new Set(questions.map(q => q.character)).size, quantity)
    assert.equal(Math.abs(questions.filter(q => q.language === 'zh-Hant-TW').length * 2 - quantity), 1)
  }
  const endless = { ...selection, mode: 'endless', quantity: 3 }
  const cycle = drawQuestions(fixture, endless, () => 0)
  const next = drawQuestions(fixture, endless, () => 0, cycle[0].character)
  assert.notEqual(next[0].character, cycle[0].character)
  assert.deepEqual(new Set(next.map(q => q.character)), new Set(cycle.map(q => q.character)))
  let round = startRound('characters', [cycle[0]], 5)
  round = practiceReducer(round, { type: 'skip' })
  round = practiceReducer(round, { type: 'continue', exercises: next })
  assert.equal(round.index, 0)
  assert.equal(roundStats(round).skipped, 1)
  round = practiceReducer(round, { type: 'end' })
  assert.equal(practiceReducer(round, { type: 'skip' }), round)
})
