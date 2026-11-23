export interface Exercise {
  character: string
  code: string
  alternateCodes?: readonly string[]
  language?: 'zh-Hant-TW' | 'zh-Hans-CN'
}

export type LessonId = 'roots' | 'characters'

type Outcome = 'firstTry' | 'retried' | 'skipped'

export interface Round {
  lesson: LessonId
  codeLimit: number
  exercises: readonly Exercise[]
  index: number
  completed: number
  solved: number
  firstTry: number
  previous?: Exercise
  previousOutcome?: Outcome
  ended: boolean
  entry: string
  hint: boolean
  wrongEntries: number
  acceptedCode?: string
}

export type Action =
  | { type: 'start'; round: Round }
  | { type: 'edit'; value: string }
  | { type: 'append'; key: string }
  | { type: 'continue'; exercises: Exercise[] }
  | { type: 'end' }
  | { type: 'hint' }
  | { type: 'submit' }
  | { type: 'skip' }

export function startRound(lesson: LessonId, exercises: readonly Exercise[], codeLimit: number): Round {
  return { lesson, exercises, codeLimit, index: 0, completed: 0, solved: 0, firstTry: 0, ended: false, entry: '', hint: false, wrongEntries: 0 }
}

export function roundStats(round: Round) {
  const { completed, solved, firstTry } = round
  return {
    completed,
    solved,
    skipped: completed - solved,
    accuracy: completed ? Math.round(firstTry * 100 / completed) : null,
  }
}

export function practiceReducer(round: Round, action: Action): Round {
  if (action.type === 'start') return action.round
  if (round.ended) return round
  if (action.type === 'end') return { ...round, ended: true }
  if (action.type === 'continue') {
    if (round.index < round.exercises.length) return round
    return { ...round, exercises: action.exercises, index: 0 }
  }
  const exercise = round.exercises[round.index]
  if (!exercise) return round
  const codes = [exercise.code, ...(exercise.alternateCodes ?? [])]

  switch (action.type) {
    case 'edit':
    case 'append': {
      const value = action.type === 'edit' ? action.value : round.entry + action.key
      const code = value.replace(/[^a-z]/gi, '').toUpperCase()
      const entry = code.slice(0, round.codeLimit)
      if (entry === code && codes.includes(entry)
        && !codes.some((answer) => answer.length > entry.length && answer.startsWith(entry))) {
        return solve(round, entry)
      }
      return { ...round, entry }
    }
    case 'hint':
      return { ...round, hint: !round.hint }
    case 'submit':
      if (!round.entry) return round
      if (!codes.includes(round.entry)) {
        return { ...round, entry: '', wrongEntries: round.wrongEntries + 1 }
      }
      return solve(round, round.entry)
    case 'skip':
      return advance(round, 'skipped')
  }
}

function solve(round: Round, code: string): Round {
  return advance(round, round.wrongEntries ? 'retried' : 'firstTry', code)
}

function advance(round: Round, outcome: Outcome, acceptedCode?: string): Round {
  return {
    ...round, entry: '', hint: false, wrongEntries: 0,
    index: round.index + 1,
    previous: round.exercises[round.index],
    previousOutcome: outcome,
    completed: round.completed + 1,
    solved: round.solved + Number(outcome !== 'skipped'),
    firstTry: round.firstTry + Number(outcome === 'firstTry'),
    acceptedCode,
  }
}
