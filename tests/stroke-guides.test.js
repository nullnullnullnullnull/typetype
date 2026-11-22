import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'

const load = path => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'))
const { codes } = load('../public/dictionaries.json')
const guides = {}
for (let i = 0; i < 64; i++) {
  const bucket = load(`../public/stroke-guides/${i}.json`).characters
  for (const [char, guide] of Object.entries(bucket)) {
    assert.equal(char.codePointAt(0) % 64, i)
    guides[char] = guide
  }
}

test('every practice character ships its reviewed diagram', () => {
  const reviews = load('../scripts/reviewed-stroke-guides.json')
  assert.deepEqual(Object.keys(guides).sort(), Object.keys(codes).sort())
  for (const [char, guide] of Object.entries(guides)) {
    const json = JSON.stringify(guide, Object.keys(guide).sort())
    assert.equal(createHash('sha256').update(json).digest('hex'), reviews[char], char)
  }
})

test('each mapped step matches its primary code and highlights real geometry', () => {
  for (const [char, { code, labels, paths, omissions }] of Object.entries(guides)) {
    assert.equal(code, codes[char][0], char)
    assert.equal(labels.length, code.length, char)
    const owners = new Set()
    for (const [step, path] of paths) {
      assert.ok(Number.isInteger(step) && step >= -1 && step < code.length, char)
      assert.match(path, /^M/, char)
      owners.add(step)
    }
    for (let i = 0; i < code.length; i++) assert.ok(owners.has(i) && labels[i], char)
    assert.equal(omissions.length > 0, owners.has(-1), char)
  }
})

test('directory examples include repeated roots and a segmented vertical in 董', () => {
  for (const c of '董明林休國') assert.ok(guides[c], c)
  const { paths, omissions } = guides.董
  assert.equal(paths.filter(([step]) => step === 0).length, 4)
  assert.deepEqual(paths.filter(([, d]) => d.startsWith('M50')).map(([step]) => step), [2, -1, 3])
  assert.match(omissions.join(''), /HJWG.*HJG/)
  assert.equal(guides.林.code, 'DD')
})

test('compound and crossing shapes retain their reviewed stroke fragments', () => {
  for (const c of '門問集') {
    assert.ok(guides[c].medians, c)
    assert.ok(guides[c].paths.some(([owner]) => owner === -1), c)
    assert.ok(guides[c].omissions.length, c)
  }
  assert.deepEqual(guides.力.paths.map(([owner]) => owner), [0, 1, 0])
  assert.deepEqual(guides.申.paths.slice(-3).map(([owner]) => owner), [0, 1, 2])
})

test('animal and enclosure components keep their stroke assignments inside words', () => {
  assert.deepEqual(guides.狗.paths.slice(0, 3).map(([owner]) => owner), [0, 0, 1])
  assert.deepEqual(guides.巴.paths.slice(-2).map(([owner]) => owner), [0, 1])
  assert.deepEqual(guides.巾.paths.map(([owner]) => owner), [1, 1, 0])
})
