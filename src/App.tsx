import { useEffect, useReducer, useRef, useState, useSyncExternalStore, type FormEvent } from 'react'
import { lessons, roots } from './cangjie'
import { availableCount, drawQuestions, readSettings, roundSize, saveSettings, type CodeTable, type Dictionaries, type Settings } from './dictionaries'
import { practiceReducer, roundStats, startRound, type LessonId } from './practice'
import { StrokeDirectory, StrokeGuide } from './StrokeGuide'
import { PracticeSettings } from './PracticeSettings'

const lessonIds: LessonId[] = ['roots', 'characters']
const keyboardRows = ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM']
const methods = {
  cangjie: {
    edition: '倉頡五代',
    title: '倉頡練習',
    intro: '從字根鍵位到常用字取碼，練習用英文字母打出倉頡碼。',
    prompt: '輸入這個字的完整倉頡碼。',
    codeLabel: '倉頡碼',
    keyboard: '倉頡鍵盤',
    codeLimit: 5,
    reference: 'https://www.cjhk.org/software/vnote.pdf',
    referenceLabel: '五代倉頡取碼參考',
    language: 'zh-Hant',
  },
  tiger: {
    edition: '虎码',
    title: '虎码练习',
    intro: '用常用繁简字练习虎码单字取码。',
    prompt: '输入这个字的虎码。',
    codeLabel: '虎码',
    keyboard: '虎码键盘',
    codeLimit: 4,
    reference: 'https://assets.tiger-code.com/docs/tutorials',
    referenceLabel: '虎码取码教程',
    language: 'zh-Hans',
  },
}
type MethodId = keyof typeof methods

function currentMethod(): MethodId {
  return window.location.hash === '#tiger' ? 'tiger' : 'cangjie'
}

function subscribeToMethod(onChange: () => void) {
  window.addEventListener('hashchange', onChange)
  return () => window.removeEventListener('hashchange', onChange)
}

export function App({ dictionaries }: { dictionaries: Dictionaries }) {
  const methodId = useSyncExternalStore(subscribeToMethod, currentMethod)
  const [sharedSettings, setSharedSettings] = useState(readSettings)
  const [tigerCodes, setTigerCodes] = useState<CodeTable>()
  const [loadError, setLoadError] = useState(false)

  useEffect(() => {
    document.title = `${methods[methodId].title} · TypeType`
    if (methodId !== 'tiger' || tigerCodes) return
    const controller = new AbortController()
    setLoadError(false)
    void (async () => {
      try {
        const response = await fetch(`${import.meta.env.BASE_URL}tiger-codes.json`, { signal: controller.signal })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const codes: CodeTable = await response.json()
        if (!controller.signal.aborted) setTigerCodes(codes)
      } catch (error) {
        if (!controller.signal.aborted) {
          console.error('Cannot load the Tiger code table', error)
          setLoadError(true)
        }
      }
    })()
    return () => controller.abort()
  }, [methodId, tigerCodes])

  function rememberSettings(settings: Settings) {
    if (!settings.banks.length) return
    setSharedSettings(settings)
    saveSettings(settings)
  }

  const codes = methodId === 'tiger' ? tigerCodes : dictionaries.codes

  return (
    <>
      <header className="site-header">
        <div className="shell header-inner">
          <div className="brand" aria-label="TypeType">
            <span className="brand-mark" aria-hidden="true">倉</span>
            <span>Type<span className="brand-accent">Type</span><span className="brand-period">.</span></span>
          </div>
          <nav className="method-nav" aria-label="輸入法">
            <a className="mode-button" href="#cangjie" aria-current={methodId === 'cangjie' ? 'page' : undefined}>五代倉頡</a>
            <a className="mode-button" href="#tiger" aria-current={methodId === 'tiger' ? 'page' : undefined} lang="zh-Hans">虎码</a>
          </nav>
        </div>
      </header>

      {codes ? (
        <Practice key={methodId} methodId={methodId} dictionaries={{ banks: dictionaries.banks, codes }}
          initialSettings={sharedSettings} onSettingsChange={rememberSettings} />
      ) : (
        <main className="shell">
          <p role={loadError ? 'alert' : 'status'} lang="zh-Hans">
            {loadError ? '虎码码表加载失败，请刷新后重试。' : '正在加载虎码码表…'}
          </p>
        </main>
      )}
    </>
  )
}

interface PracticeProps {
  methodId: MethodId
  dictionaries: Dictionaries
  initialSettings: Settings
  onSettingsChange: (settings: Settings) => void
}

function Practice({ methodId, dictionaries, initialSettings, onSettingsChange }: PracticeProps) {
  const method = methods[methodId]
  const isCangjie = methodId === 'cangjie'
  const [settings, setSettings] = useState(initialSettings)
  const [activeSettings, setActiveSettings] = useState(settings)
  const [round, dispatch] = useReducer(practiceReducer, initialSettings, (selection) =>
    startRound('characters', drawQuestions(dictionaries, selection), method.codeLimit),
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
    onSettingsChange(next)
  }

  function begin(lessonId: LessonId) {
    if (lessonId === 'characters') {
      const next = count >= roundSize ? settings : activeSettings
      dispatch({ type: 'start', round: startRound(lessonId, drawQuestions(dictionaries, next), method.codeLimit) })
      setActiveSettings(next)
      return
    }
    dispatch({ type: 'start', round: startRound(lessonId, lessons.roots.exercises, 1) })
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
        ? `答對了！「${previous.character}」的${method.codeLabel}是 ${round.acceptedCode}。`
        : ''

  return (
    <main className="shell">
      <section className="intro" aria-labelledby="page-title" lang={method.language}>
        <span className="edition">{method.edition}</span>
        <h1 id="page-title">{method.title}<span aria-hidden="true">.</span></h1>
        <p>{method.intro}</p>
      </section>

      {isCangjie && (
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
      )}

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
                <p lang={method.language}>{round.lesson === 'roots' ? lessons.roots.prompt : method.prompt}</p>
                <div className="character" lang={exercise.language}>{exercise.character}</div>
              </div>

              <form onSubmit={submit}>
                <label htmlFor="code" lang={method.language}>{method.codeLabel}</label>
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
                {feedback || '輸入正確會自動跳題，也可按 Enter 確認。'}
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
                {isCangjie && <span>{Array.from(exercise.code, (key) => roots[key]).join(' · ')}</span>}
                {!!exercise.alternateCodes?.length && (
                  <span className="alternate-codes">
                    {isCangjie ? '其他完整碼' : '其他可用编码'} {exercise.alternateCodes.join(' · ')}
                  </span>
                )}
                {isCangjie && round.lesson === 'characters' && round.hint &&
                  <StrokeGuide key={exercise.character} char={exercise.character} code={exercise.code} />}
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
              <h2 id="keyboard-title" lang={method.language}>{method.keyboard}</h2>
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
                      aria-label={isCangjie ? `${key}，${roots[key]}` : key}
                      disabled={finished}
                      onMouseDown={(event) => {
                        if (document.activeElement === input.current) event.preventDefault()
                      }}
                      onClick={() => dispatch({ type: 'append', key })}
                    >
                      {isCangjie ? <><span>{key}</span><strong>{roots[key]}</strong></> : <strong>{key}</strong>}
                    </button>
                  ))}
                </div>
              ))}
            </div>
            {isCangjie
              ? <p className="keyboard-note">X 為難字鍵，Z 為符號鍵。字根練習涵蓋 24 個基本字根。</p>
              : <p className="keyboard-note" lang="zh-Hans">虎码单字最多 4 个字母。简码也是另一有效码的开头时，可按 Enter 确认。</p>}
          </section>
        </div>
      </div>

      {isCangjie && <StrokeDirectory codes={dictionaries.codes} />}
      <details className="sources">
        <summary>字庫來源與授權</summary>
        <ul>
          <li><a href="https://www.cns11643.gov.tw/searchSY.jsp?ID=122">數位發展部 CNS11643 中文標準交換碼全字庫</a>，臺灣 4,808 字索引轉為 Unicode，採 <a href="https://data.gov.tw/license">政府資料開放授權條款第 1 版</a>。</li>
          <li><a href="https://coct.naer.edu.tw/page.jsp?ID=41">國家教育研究院《臺灣華語文能力基準漢字表》</a>，CC BY。擷取第 1 級（含第 1* 級）並與臺灣字庫比對。</li>
          <li><a href="https://www.unicode.org/reports/tr38/#kTGH">Unicode Unihan 18.0.0</a>，擷取《通用规范汉字表》一級字，採 <a href={`${import.meta.env.BASE_URL}Unicode-LICENSE.txt`}>Unicode License V3</a>。</li>
          {isCangjie ? (
            <li><a href="https://github.com/Jackchows/Cangjie5/tree/c9b64e77951cba48bdfa5de8eaedd1a908666b9b">倉頡五代補完計劃</a>，源自倉頡之友・馬來西亞《五倉世紀》。TypeType 擷取練習字的完整碼，隨附 <a href={`${import.meta.env.BASE_URL}Cangjie5-LICENSE.txt`}>MIT 版權聲明與授權全文</a>。</li>
          ) : (
            <li><a href="https://github.com/lvyww/tiger-code/tree/3e1bff2f757806152ef5b701c709c24f54cf800f">虎码官方码表</a>，擷取所選字庫的單字編碼，採 <a href={`${import.meta.env.BASE_URL}Tiger-LICENSE.txt`}>CC0 1.0</a>。</li>
          )}
        </ul>
        <p><a href={`${import.meta.env.BASE_URL}THIRD-PARTY-NOTICES.txt`}>完整第三方資料聲明</a></p>
      </details>

      <footer className="footer">
        <span>TypeType</span>
        <a href={method.reference} lang={method.language}>{method.referenceLabel}</a>
      </footer>
    </main>
  )
}
