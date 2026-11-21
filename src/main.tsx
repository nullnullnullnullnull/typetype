import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import type { Dictionaries } from './dictionaries'
import './styles.css'

const root = createRoot(document.getElementById('root')!)

async function render() {
  let dictionaries: Dictionaries
  try {
    const response = await fetch(`${import.meta.env.BASE_URL}dictionaries.json`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    dictionaries = await response.json()
  } catch (error) {
    console.error('Cannot load the Cangjie dictionaries', error)
    root.render(<p role="alert">字庫載入失敗，請重新整理後再試。</p>)
    return
  }

  root.render(
    <StrictMode>
      <App dictionaries={dictionaries} />
    </StrictMode>,
  )
}

void render()
