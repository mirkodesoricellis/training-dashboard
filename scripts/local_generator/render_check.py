import asyncio, json
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width':390,'height':844})
        errs=[]; pg.on('console', lambda m: errs.append(m.text) if m.type=='error' else None)
        await pg.goto('file:///home/claude/out/index.html')
        await pg.wait_for_timeout(600)
        r = await pg.evaluate("""() => {
          const days=[...document.querySelectorAll('.day')];
          const shown=days.filter(d=>d.classList.contains('show'));
          document.querySelectorAll('.meal').forEach(m=>m.classList.add('open'));
          return {
            days: days.length,
            shownIso: shown.map(d=>d.dataset.iso),
            todayVisible: [...document.querySelectorAll('.today')].filter(t=>!t.hidden).length,
            meals: document.querySelectorAll('.meal').length,
            pills: document.querySelectorAll('.pill').length,
            bg: getComputedStyle(document.body).backgroundColor,
            fuelCards: [...document.querySelectorAll('h2')].filter(h=>h.textContent.includes('Fueling')).length,
            insight: document.querySelectorAll('.card.ins').length,
            rec: document.querySelectorAll('.card.rec').length
          };
        }""")
        await pg.wait_for_timeout(400)
        ov = await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        r['overflowPx']=ov; r['consoleErrors']=[x for x in errs if 'favicon' not in x and '.png' not in x]
        print(json.dumps(r, indent=1, ensure_ascii=False))
        await pg.screenshot(path='/home/claude/out/preview.png', full_page=False)
        await b.close()
asyncio.run(main())
