# TypeType

在瀏覽器練習五代倉頡和虎碼。以 Vite、React、TypeScript 和原生 CSS 製作。

[開啟五代倉頡練習](https://nullnullnullnullnull.github.io/typetype/)

## 練習

- **五代倉頡**提供常用字取碼和 24 題字根鍵位練習。**虎码**提供單字取碼練習。從頁首切換輸入法時會沿用字庫和難度，開啟新的一輪。虎碼入口也可用 `#tiger` 直接開啟。
- **常用字取碼**可複選臺灣常用字（4,808 字）和大陆规范常用字（3,500 字），另選「入門」或「全字庫」。每輪隨機抽 20 個不重複的字。混合時兩庫各抽 10 題，缺額由有剩餘題目的字庫補足。可用實體鍵盤或螢幕鍵盤輸入英文字母。
- 首次使用預設為「繁體」和「入門」，瀏覽器會記住最近的有效選擇。修改字庫或難度後，下一輪才套用。
- 輸入有效編碼會自動跳題。如果短碼也是有效長碼的開頭，可按 Enter 或「確認」提交短碼。提交錯碼時會提示重試。
- 點選「顯示提示」可查閱有效編碼，倉頡也會顯示字根順序。跳題後會顯示正確碼。首答正確率是首次提交即正確的題數除以已完成題數。跳題計入已完成題數，提示不影響計分。

## 本地開發

建議使用 Node.js 24。

```sh
npm ci
npm run dev
```

```sh
npm test
npm run typecheck
npm run build
npm run preview
```

## 字庫資料

共用字庫和倉頡碼放在 `public/dictionaries.json`，虎碼單字編碼放在 `public/tiger-codes.json`。虎碼採用官方碼表中的 1–4 位單字編碼，提示優先顯示較長的有效編碼。更新題庫時可用 Python 3 重新執行生成器。

```sh
python3 scripts/generate-dictionaries.py --download
```

`--download` 只下載缺少的來源檔。生成器核對[固定版本與 SHA-256](scripts/dictionary-sources.json)，並以 CNS11643 索引中的字碼和字元順序校驗內容。來源檔和包含原始收字、可練字數、缺碼、排除碼及多碼字的報告位於 `.local/`。

字庫由數位發展部 CNS11643 全字庫、國家教育研究院漢字分級表、Unicode Unihan 及《倉頡五代補完計劃》資料整理而成。各來源的版本、署名及轉換方式見[完整第三方資料聲明](public/THIRD-PARTY-NOTICES.txt)。[倉頡字碼 MIT 授權](public/Cangjie5-LICENSE.txt)與 [Unicode License V3](public/Unicode-LICENSE.txt) 隨資料發布。取碼規則可參考[香港教育學院《第五代倉頡輸入法》](https://www.cjhk.org/software/vnote.pdf)。

虎碼取碼使用 [虎碼官方碼表](https://github.com/lvyww/tiger-code) 的固定版本，隨附 [CC0 1.0 授權](public/Tiger-LICENSE.txt)。取碼方法見 [虎碼官方教程](https://assets.tiger-code.com/docs/tutorials)。

## GitHub Pages

儲存庫的 **Settings → Pages → Build and deployment** 使用 **GitHub Actions**。推送到 `main` 後，工作流程會安裝依賴、執行測試及型別檢查，並部署 `dist/`。也可以從 **Actions → Deploy TypeType to GitHub Pages** 手動執行。構建使用相對資產路徑，可部署到儲存庫子路徑。
