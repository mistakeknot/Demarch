(() => {
  try {
    const spacingMap = {};
    const spacingProps = ['marginTop', 'marginRight', 'marginBottom', 'marginLeft',
                          'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
                          'gap', 'rowGap', 'columnGap'];
    const elements = document.querySelectorAll('body *');
    const sampleLimit = Math.min(elements.length, 1500);

    for (let i = 0; i < sampleLimit; i++) {
      const styles = getComputedStyle(elements[i]);
      for (const prop of spacingProps) {
        const val = styles[prop];
        if (val && val !== '0px' && val !== 'auto' && val !== 'normal') {
          const px = parseFloat(val);
          if (!isNaN(px) && px > 0 && px < 500) {
            const key = px + 'px';
            if (!spacingMap[key]) {
              spacingMap[key] = { value: px, unit: 'px', frequency: 0 };
            }
            spacingMap[key].frequency++;
          }
        }
      }
    }

    const sorted = Object.values(spacingMap)
      .sort((a, b) => a.value - b.value)
      .slice(0, 20);

    return JSON.stringify({ count: sorted.length, spacing: sorted });
  } catch (e) {
    return JSON.stringify({ count: 0, spacing: [], error: e.message });
  }
})()
