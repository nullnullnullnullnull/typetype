# TypeType

在瀏覽器練習輸入法。首個練習為第五代倉頡，使用繁體中文介面。以 Vite、React、TypeScript 和原生 CSS 製作。

## 五代倉頡練習

- **字根鍵位**有 24 題，練習基本字根對應的英文字母。
- **常用字取碼**有 18 題，練習輸入完整倉頡碼。可用實體鍵盤輸入英文字母後按 Enter，或點選畫面上的按鍵和「確認」。
- 點選「顯示提示」可查看取碼及字根順序。答錯可重試，跳題後會顯示正確碼。切換模式或重新開始會開啟新的一輪。
- 首答正確率以首次提交即正確的題數除以已完成題數。跳過的題目計入已完成題數，提示不影響計分。

題庫為手選的入門練習，常用字的完整碼已逐題對照 [Rime 五代倉頡單字碼表](https://github.com/rime/rime-cangjie/blob/master/cangjie5.base.dict.yaml)。取碼規則可參考 [香港教育學院《第五代倉頡輸入法》](https://www.cjhk.org/software/vnote.pdf)。

## 本地開發

建議使用 Node.js 24。

```sh
npm ci
npm run dev
```

```sh
npm run typecheck
npm run build
npm run preview
```

題庫和鍵位資料在 `src/cangjie.ts`，練習流程與統計在 `src/practice.ts`，介面在 `src/App.tsx`。

## GitHub Pages

1. 在 GitHub 建立公開儲存庫，將專案提交並推送到 `main`。
2. 在儲存庫的 **Settings → Pages → Build and deployment** 裡，將 **Source** 設為 **GitHub Actions**。
3. 第一次啟用 Pages 後，可從 **Actions → Deploy TypeType to GitHub Pages** 手動執行。之後推送到 `main` 會自動部署，工作流程會顯示上線網址。

工作流程執行型別檢查並建置 `dist/`。Vite 使用相對資產路徑，同一份產物可用於 GitHub Pages 的儲存庫子路徑。
