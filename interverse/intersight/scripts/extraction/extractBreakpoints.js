(() => {
  try {
    const breakpoints = new Set();

    for (const sheet of document.styleSheets) {
      try {
        for (const rule of sheet.cssRules || []) {
          if (rule instanceof CSSMediaRule) {
            const text = rule.conditionText || rule.media?.mediaText || '';
            const matches = text.match(/\d+(?:\.\d+)?px/g);
            if (matches) {
              for (const m of matches) {
                const px = parseFloat(m);
                if (px >= 320 && px <= 2560) {
                  breakpoints.add(px);
                }
              }
            }
          }
        }
      } catch (_) {
        // Cross-origin stylesheet — skip silently
      }
    }

    const sorted = Array.from(breakpoints)
      .sort((a, b) => a - b)
      .map(px => ({ value: px, unit: 'px' }));

    return JSON.stringify({ count: sorted.length, breakpoints: sorted });
  } catch (e) {
    return JSON.stringify({ count: 0, breakpoints: [], error: e.message });
  }
})()
