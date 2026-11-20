export interface Exercise {
  character: string
  code: string
}

const keyLetters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
const rootLabels = '日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜符'

export const roots = Object.fromEntries(
  Array.from(keyLetters, (key, index) => [key, rootLabels[index]]),
)

export const keyboardRows = ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM']

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
    prompt: '輸入這個字的完整倉頡碼。',
    exercises: [
      { character: '明', code: 'AB' },
      { character: '林', code: 'DD' },
      { character: '休', code: 'OD' },
      { character: '好', code: 'VND' },
      { character: '你', code: 'ONF' },
      { character: '中', code: 'L' },
      { character: '日', code: 'A' },
      { character: '問', code: 'ANR' },
      { character: '品', code: 'RRR' },
      { character: '森', code: 'DDD' },
      { character: '晶', code: 'AAA' },
      { character: '字', code: 'JND' },
      { character: '安', code: 'JV' },
      { character: '江', code: 'EM' },
      { character: '唱', code: 'RAA' },
      { character: '信', code: 'OYMR' },
      { character: '語', code: 'YRMMR' },
      { character: '學', code: 'HBND' },
    ] satisfies Exercise[],
  },
}

export type LessonId = keyof typeof lessons
