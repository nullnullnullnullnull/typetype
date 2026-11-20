import { lessons, type LessonId } from './cangjie'

type Outcome = 'firstTry' | 'retried' | 'skipped'

export interface Round {
  lesson: LessonId
  outcomes: Outcome[]
  entry: string
  hint: boolean
  wrongEntries: number
}

export type Action =
  | { type: 'start'; lesson: LessonId }
  | { type: 'edit'; value: string }
  | { type: 'append'; key: string }
  | { type: 'hint' }
  | { type: 'submit' }
  | { type: 'skip' }

export function startRound(lesson: LessonId): Round {
  return { lesson, outcomes: [], entry: '', hint: false, wrongEntries: 0 }
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
  if (action.type === 'start') return startRound(action.lesson)
  const exercise = lessons[round.lesson].exercises[round.outcomes.length]
  if (!exercise) return round

  switch (action.type) {
    case 'edit':
    case 'append': {
      const value = action.type === 'edit' ? action.value : round.entry + action.key
      const limit = round.lesson === 'roots' ? 1 : 5
      return { ...round, entry: value.replace(/[^a-z]/gi, '').toUpperCase().slice(0, limit) }
    }
    case 'hint':
      return { ...round, hint: !round.hint }
    case 'submit':
      if (!round.entry) return round
      if (round.entry !== exercise.code) {
        return { ...round, entry: '', wrongEntries: round.wrongEntries + 1 }
      }
      return advance(round, round.wrongEntries ? 'retried' : 'firstTry')
    case 'skip':
      return advance(round, 'skipped')
  }
}

function advance(round: Round, outcome: Outcome): Round {
  return { ...startRound(round.lesson), outcomes: [...round.outcomes, outcome] }
}
