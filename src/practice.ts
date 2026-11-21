import type { Exercise, LessonId } from './cangjie'

type Outcome = 'firstTry' | 'retried' | 'skipped'

export interface Round {
  lesson: LessonId
  exercises: readonly Exercise[]
  outcomes: Outcome[]
  entry: string
  hint: boolean
  wrongEntries: number
  acceptedCode?: string
}

export type Action =
  | { type: 'start'; round: Round }
  | { type: 'edit'; value: string }
  | { type: 'append'; key: string }
  | { type: 'hint' }
  | { type: 'submit' }
  | { type: 'skip' }

export function startRound(lesson: LessonId, exercises: readonly Exercise[]): Round {
  return { lesson, exercises, outcomes: [], entry: '', hint: false, wrongEntries: 0 }
}

export function roundStats(round: Round) {
  const completed = round.outcomes.length
  const firstTry = round.outcomes.filter((outcome) => outcome === 'firstTry').length
  const solved = round.outcomes.filter((outcome) => outcome !== 'skipped').length
  return {
    completed,
    solved,
    skipped: completed - solved,
    accuracy: completed ? Math.round(firstTry * 100 / completed) : null,
  }
}

export function practiceReducer(round: Round, action: Action): Round {
  if (action.type === 'start') return action.round
  const exercise = round.exercises[round.outcomes.length]
  if (!exercise) return round
  const codes = [exercise.code, ...(exercise.alternateCodes ?? [])]

  switch (action.type) {
    case 'edit':
    case 'append': {
      const value = action.type === 'edit' ? action.value : round.entry + action.key
      const limit = round.lesson === 'roots' ? 1 : 5
      const code = value.replace(/[^a-z]/gi, '').toUpperCase()
      const entry = code.slice(0, limit)
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
    ...startRound(round.lesson, round.exercises),
    outcomes: [...round.outcomes, outcome],
    acceptedCode,
  }
}
