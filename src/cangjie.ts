import type { Exercise } from './practice'

const keyLetters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
const rootLabels = '日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜符'

export const roots = Object.fromEntries(
  Array.from(keyLetters, (key, index) => [key, rootLabels[index]]),
)

export const lessons = {
  roots: {
    label: '字根鍵位',
    prompt: '這個字根對應哪個英文字母？',
    exercises: Array.from('ABCDEFGHIJKLMNOPQRSTUVWY',
      (code): Exercise => ({ character: roots[code], code }),
    ),
  },
  characters: {
    label: '常用字取碼',
  },
}
