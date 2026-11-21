export interface Exercise {
  character: string
  code: string
  alternateCodes?: readonly string[]
  language?: 'zh-Hant-TW' | 'zh-Hans-CN'
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
  },
}

export type LessonId = keyof typeof lessons
