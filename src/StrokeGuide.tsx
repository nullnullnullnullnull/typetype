import { useEffect, useState } from 'react'
import { roots } from './cangjie'
import type { CodeTable } from './dictionaries'

interface Diagram {
  code: string
  labels: string[]
  omissions: string[]
  paths: [number, string][]
  medians?: boolean
  variant?: string
  composed?: boolean
  schematic?: boolean
}

const chunks = new Map<number, Promise<Record<string, Diagram>>>()

function loadDiagram(char: string) {
  const bucket = char.codePointAt(0)! % 64
  let chunk = chunks.get(bucket)
  if (!chunk) {
    chunk = fetch(`${import.meta.env.BASE_URL}stroke-guides/${bucket}.json`).then(response => {
      if (!response.ok) throw new Error(String(response.status))
      return response.json().then((chunk: { characters: Record<string, Diagram> }) => chunk.characters)
    }).catch(error => {
      chunks.delete(bucket)
      throw error
    })
    chunks.set(bucket, chunk)
  }
  return chunk.then(data => data[char])
}

export function StrokeGuide({ char, code }: { char: string, code: string }) {
  const [diagram, setDiagram] = useState<Diagram>()
  const [step, setStep] = useState(0)
  const [status, setStatus] = useState('載入筆畫圖解中…')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    loadDiagram(char).then(result => {
      if (!active) return
      if (result?.code === code) setDiagram(result)
      else setStatus('這個字的逐筆標註尚待核對。')
    }).catch(() => { if (active) setStatus('圖解載入失敗。') })
    return () => { active = false }
  }, [char, code, attempt])
  if (!diagram) return <p role="status">{status} {status === '圖解載入失敗。' &&
    <button type="button" onClick={() => { setStatus('載入筆畫圖解中…'); setAttempt(attempt + 1) }}>重試</button>}</p>
  const outline = diagram.schematic || diagram.medians
  const selected = code[step]
  // A shared stroke can belong to two roots. Paint the selected root last.
  const paths = [...diagram.paths.filter(([owner]) => owner !== step),
    ...diagram.paths.filter(([owner]) => owner === step)]
  return <div className="stroke-guide">
    <svg viewBox={diagram.schematic ? '0 0 100 100' : '0 0 1024 1024'} role="img"
      aria-label={`${char}，第 ${step+1} 碼 ${selected}：${diagram.labels[step]}`}>
      <g transform={diagram.schematic ? undefined : 'translate(0 900) scale(1 -1)'}>
        {paths.map(([owner, path], i) => {
          const color = owner === step ? '#542bb0' : owner < 0 ? '#aaa9a5' : '#495e6a'
          return <path key={i} d={path} data-step={owner}
            fill={outline ? 'none' : color} stroke={outline ? color : undefined}
            strokeWidth={diagram.medians ? 26 : 2.7} strokeLinecap="round" strokeLinejoin="round" />
        })}
      </g>
    </svg>
    <div>
      <div className="stroke-steps" role="group" aria-label={`${char}的取碼順序`}>
        {Array.from(code, (key, i) => <button type="button" key={i} className="mode-button"
          aria-label={`第 ${i+1} 碼 ${key} ${roots[key]}`} aria-pressed={step === i}
          onClick={() => setStep(i)}>{key} {roots[key]}</button>)}
      </div>
      <p aria-live="polite">第 {step+1} 碼 · {selected} {roots[selected]} · {diagram.labels[step]}</p>
      {diagram.omissions.map(reason => <p key={reason}>灰色省略部分 · {reason}</p>)}
      <small>{diagram.schematic ? '臺灣標準字形示意' : diagram.variant ?? (diagram.composed ? '依部件組合的筆形示意' : 'Make Me a Hanzi 筆形')} · 紫色標出所選字根</small>
    </div>
  </div>
}

export function StrokeDirectory({ codes }: { codes: CodeTable }) {
  const [char, setChar] = useState('董')
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  function select(next: string) {
    if (Array.from(next).length !== 1 || !Object.hasOwn(codes, next)) { setError('請輸入繁簡字庫中的一個字。'); return }
    setError('')
    setChar(next)
    setQuery(next)
  }
  return <details className="sources panel" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>倉頡拆字導覽</summary>
    {open && <>
      <form className="guide-search" onSubmit={event => { event.preventDefault(); select(query.trim()) }}>
        <label>查找單字 <input value={query} onChange={event => setQuery(event.target.value)} /></label>
        <button className="button button-small" type="submit">查找</button>
      </form>
      {error && <p role="alert">{error}</p>}
      <div className="stroke-steps" aria-label="圖解示例">{Array.from('董明林休國', c =>
        <button key={c} className="mode-button" aria-pressed={char === c} onClick={() => select(c)}>{c}</button>)}</div>
      <h3>{char} · {codes[char][0]}</h3>
      <StrokeGuide key={char} char={char} code={codes[char][0]} />
    </>}
  </details>
}
