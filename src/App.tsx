import { useEffect, useReducer, useRef, useState, type FormEvent } from 'react'
import { keyboardRows, lessons, roots, type LessonId } from './cangjie'
import { availableCount, drawQuestions, readSettings, roundSize, saveSettings, type Dictionaries, type Settings } from './dictionaries'
import { practiceReducer, roundStats, startRound } from './practice'
import { PracticeSettings } from './PracticeSettings'

const lessonIds: LessonId[] = ['roots', 'characters']

export function App({ dictionaries }: { dictionaries: Dictionaries }) {
  const [settings, setSettings] = useState(readSettings)
  const [activeSettings, setActiveSettings] = useState(settings)
  const [round, dispatch] = useReducer(practiceReducer, settings, (initialSettings) =>
    startRound('characters', drawQuestions(dictionaries, initialSettings)),
  )
  const input = useRef<HTMLInputElement>(null)
  const summary = useRef<HTMLHeadingElement>(null)

  const lesson = lessons[round.lesson]
  const total = round.exercises.length
  const stats = roundStats(round)
  const exercise = round.exercises[stats.completed]
  const finished = stats.completed === total
  const previous = round.exercises[stats.completed - 1]
  const previousOutcome = round.outcomes.at(-1)
  const accuracy = stats.accuracy === null ? '—' : `${stats.accuracy}%`
  const count = availableCount(dictionaries, settings)
  const canRestart = round.lesson === 'roots' || count >= roundSize
  const pending = activeSettings.difficulty !== settings.difficulty
    || activeSettings.banks.length !== settings.banks.length
    || settings.banks.some((bank) => !activeSettings.banks.includes(bank))

  useEffect(() => {
    if (finished) summary.current?.focus()
  }, [finished])

  function changeSettings(next: Settings) {
    setSettings(next)
    saveSettings(next)
  }

  function begin(lessonId: LessonId) {
    if (lessonId === 'characters') {
      const next = count >= roundSize ? settings : activeSettings
      dispatch({ type: 'start', round: startRound(lessonId, drawQuestions(dictionaries, next)) })
      setActiveSettings(next)
      return
    }
    dispatch({ type: 'start', round: startRound(lessonId, lessons.roots.exercises) })
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (round.entry) dispatch({ type: 'submit' })
    if (window.matchMedia('(pointer: fine)').matches) input.current?.focus()
  }

  const feedback = round.wrongEntries
    ? `再試一次！這題已答錯 ${round.wrongEntries} 次。`
    : previousOutcome === 'skipped'
      ? `已跳過「${previous.character}」，正確碼是 ${previous.code}。`
      : previous
        ? `答對了！「${previous.character}」的倉頡碼是 ${round.acceptedCode}。`
        : ''

  return (
    <>
      <header className="site-header">
        <div className="shell header-inner">
          <div className="brand" aria-label="TypeType">
            <span className="brand-mark" aria-hidden="true">倉</span>
            <span>Type<span className="brand-accent">Type</span><span className="brand-period">.</span></span>
          </div>
          <span className="header-label">輸入法練習</span>
        </div>
      </header>

      <main className="shell">
        <section className="intro" aria-labelledby="page-title">
          <span className="edition">倉頡五代</span>
          <h1 id="page-title">倉頡練習<span aria-hidden="true">.</span></h1>
          <p>從字根鍵位到常用字取碼，練習用英文字母打出倉頡碼。</p>
        </section>

        <div className="mode-bar" role="group" aria-label="練習模式">
          {lessonIds.map((id) => (
            <button
              type="button"
              key={id}
              aria-pressed={id === round.lesson}
              className="mode-button"
              onClick={() => {
                if (id !== round.lesson) begin(id)
              }}
            >
              {lessons[id].label}
            </button>
          ))}
        </div>

        {round.lesson === 'characters' && (
          <PracticeSettings dictionaries={dictionaries} settings={settings} count={count}
            pending={pending} onChange={changeSettings} onStart={() => begin('characters')} />
        )}

        <div className="workspace">
          <section className="panel practice-panel" aria-label={lesson.label}>
            <div className="panel-heading">
              <h2>{lesson.label}</h2>
              <span className="question-count">{finished ? total : stats.completed + 1} / {total} 題</span>
            </div>

            {exercise ? (
              <>
                <div className="question" aria-live="polite" aria-atomic="true">
                  <p>{lesson.prompt}</p>
                  <div className="character" lang={exercise.language}>{exercise.character}</div>
                </div>

                <form onSubmit={submit}>
                  <label htmlFor="code">倉頡碼</label>
                  <div className="answer-row">
                    <input
                      id="code"
                      ref={input}
                      type="text"
                      autoComplete="off"
                      autoCapitalize="characters"
                      spellCheck={false}
                      lang="en"
                      aria-describedby="answer-feedback"
                      placeholder={round.lesson === 'roots' ? '輸入 1 個字母' : '輸入 A–Z'}
                      value={round.entry}
                      onChange={(event) => dispatch({ type: 'edit', value: event.target.value })}
                    />
                    <button className="button button-primary" type="submit" disabled={!round.entry}>
                      確認 <kbd aria-hidden="true">↵</kbd>
                    </button>
                  </div>
                </form>

                <div className={round.wrongEntries ? 'feedback feedback-error' : 'feedback'} id="answer-feedback" role="status">
                  {feedback || '按 Enter 確認，也可以點選螢幕鍵盤。'}
                </div>

                <div className="question-actions">
                  <button className="button button-small" type="button" aria-expanded={round.hint} aria-controls="hint"
                    onClick={() => dispatch({ type: 'hint' })}>
                    {round.hint ? '收起提示' : '顯示提示'}
                  </button>
                  <button className="button button-small" type="button" onClick={() => dispatch({ type: 'skip' })}>
                    跳過
                  </button>
                </div>

                <div className="hint" id="hint" hidden={!round.hint}>
                  <strong>{exercise.code}</strong>
                  <span>{Array.from(exercise.code, (key) => roots[key]).join(' · ')}</span>
                  {!!exercise.alternateCodes?.length && (
                    <span className="alternate-codes">其他完整碼 {exercise.alternateCodes.join(' · ')}</span>
                  )}
                </div>
              </>
            ) : (
              <div className="summary">
                <h3 tabIndex={-1} ref={summary}>本輪完成！</h3>
                <p>答對 {stats.solved} 題，跳過 {stats.skipped} 題。首答正確率 {accuracy}。</p>
                <p className="feedback">{feedback}</p>
                <button className="button button-primary" type="button" disabled={!canRestart}
                  onClick={() => begin(round.lesson)}>
                  再練一輪
                </button>
              </div>
            )}
          </section>

          <div className="sidebar">
            <section className="panel progress-panel" aria-labelledby="progress-title">
              <div className="panel-heading">
                <h2 id="progress-title">本輪進度</h2>
                <button className="text-button" type="button" disabled={!canRestart}
                  onClick={() => begin(round.lesson)}>
                  重新開始
                </button>
              </div>
              <dl className="metrics">
                <div><dt>已完成</dt><dd>{stats.completed}<span> / {total}</span></dd></div>
                <div><dt>首答正確率</dt><dd>{accuracy}</dd></div>
              </dl>
              <progress value={stats.completed} max={total} aria-labelledby="progress-title" />
            </section>

            <section className="panel keyboard-panel" aria-labelledby="keyboard-title">
              <div className="panel-heading">
                <h2 id="keyboard-title">倉頡鍵盤</h2>
                <span className="keyboard-label">QWERTY</span>
              </div>
              <div className="keyboard">
                {keyboardRows.map((row) => (
                  <div key={row} className="key-row">
                    {Array.from(row, (key) => (
                      <button
                        key={key}
                        type="button"
                        className={round.hint && exercise?.code.includes(key) ? 'key key-hint' : 'key'}
                        aria-label={`${key}，${roots[key]}`}
                        disabled={finished}
                        onMouseDown={(event) => {
                          if (document.activeElement === input.current) event.preventDefault()
                        }}
                        onClick={() => dispatch({ type: 'append', key })}
                      >
                        <span>{key}</span><strong>{roots[key]}</strong>
                      </button>
                    ))}
                  </div>
                ))}
              </div>
              <p className="keyboard-note">X 為難字鍵，Z 為符號鍵。字根練習涵蓋 24 個基本字根。</p>
            </section>
          </div>
        </div>

        <details className="sources">
          <summary>字庫來源與授權</summary>
          <ul>
            <li><a href="https://www.cns11643.gov.tw/searchSY.jsp?ID=122">數位發展部 CNS11643 中文標準交換碼全字庫</a>，臺灣 4,808 字索引轉為 Unicode，採 <a href="https://data.gov.tw/license">政府資料開放授權條款第 1 版</a>。</li>
            <li><a href="https://coct.naer.edu.tw/page.jsp?ID=41">國家教育研究院《臺灣華語文能力基準漢字表》</a>，CC BY。擷取第 1 級（含第 1* 級）並與臺灣字庫比對。</li>
            <li><a href="https://www.unicode.org/reports/tr38/#kTGH">Unicode Unihan 18.0.0</a>，擷取《通用规范汉字表》一級字，採 <a href={`${import.meta.env.BASE_URL}Unicode-LICENSE.txt`}>Unicode License V3</a>。</li>
            <li><a href="https://github.com/Jackchows/Cangjie5/tree/c9b64e77951cba48bdfa5de8eaedd1a908666b9b">倉頡五代補完計劃</a>，源自倉頡之友・馬來西亞《五倉世紀》。TypeType 擷取練習字的完整碼，隨附 <a href={`${import.meta.env.BASE_URL}Cangjie5-LICENSE.txt`}>MIT 版權聲明與授權全文</a>。</li>
          </ul>
          <p><a href={`${import.meta.env.BASE_URL}THIRD-PARTY-NOTICES.txt`}>完整第三方資料聲明</a></p>
        </details>

        <footer className="footer">
          <span>TypeType</span>
          <a href="https://www.cjhk.org/software/vnote.pdf">五代倉頡取碼參考</a>
        </footer>
      </main>
    </>
  )
}
