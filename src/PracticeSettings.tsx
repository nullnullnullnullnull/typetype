import { banks, roundSize, type Dictionaries, type Settings } from './dictionaries'

const bankLabels = {
  traditional: '臺灣常用字',
  simplified: '大陆规范常用字',
}

const presets: { label: string; banks: Settings['banks'] }[] = [
  { label: '繁體', banks: ['traditional'] },
  { label: '简体', banks: ['simplified'] },
  { label: '混合', banks: [...banks] },
]

interface Props {
  dictionaries: Dictionaries
  settings: Settings
  count: number
  pending: boolean
  onChange: (settings: Settings) => void
  onStart: () => void
}

export function PracticeSettings({ dictionaries, settings, count, pending, onChange, onStart }: Props) {
  return (
    <section className="panel settings-panel" aria-label="取碼練習設定">
      <div className="settings-fields">
        <fieldset>
          <legend>練習字庫</legend>
          <div className="bank-presets" role="group" aria-label="字庫快捷選項">
            {presets.map((preset) => (
              <button key={preset.label} className="button button-small" type="button"
                aria-pressed={preset.banks.length === settings.banks.length && preset.banks.every((bank) => settings.banks.includes(bank))}
                onClick={() => onChange({ ...settings, banks: preset.banks })}>
                {preset.label}
              </button>
            ))}
          </div>
          <div className="bank-options">
            {banks.map((bank) => (
              <label key={bank}>
                <input type="checkbox" checked={settings.banks.includes(bank)}
                  onChange={(event) => onChange({
                    ...settings,
                    banks: event.target.checked
                      ? [...settings.banks, bank]
                      : settings.banks.filter((selected) => selected !== bank),
                  })} />
                <span lang={bank === 'simplified' ? 'zh-Hans' : undefined}>{bankLabels[bank]}</span>
                <span className="bank-count">{dictionaries.banks[bank][settings.difficulty].length.toLocaleString()}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend>難度</legend>
          <div className="difficulty-options">
            <label>
              <input name="difficulty" type="radio" checked={settings.difficulty === 'beginner'}
                onChange={() => onChange({ ...settings, difficulty: 'beginner' })} />
              入門
            </label>
            <label>
              <input name="difficulty" type="radio" checked={settings.difficulty === 'full'}
                onChange={() => onChange({ ...settings, difficulty: 'full' })} />
              全字庫
            </label>
          </div>
        </fieldset>
      </div>
      <div className="settings-footer">
        <p aria-live="polite">
          {settings.banks.length === 0
            ? '請至少選擇一個字庫。'
            : `可練 ${count.toLocaleString()} 字 · 每輪 ${roundSize} 題${pending ? ' · 下輪套用' : ''}`}
        </p>
        {pending && count >= roundSize && (
          <button className="button button-small" type="button" onClick={onStart}>
            套用並開新一輪
          </button>
        )}
      </div>
    </section>
  )
}
