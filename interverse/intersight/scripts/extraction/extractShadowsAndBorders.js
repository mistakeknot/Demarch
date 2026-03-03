(() => {
  try {
    const shadowMap = {};
    const borderMap = {};
    const elements = document.querySelectorAll('body *');
    const sampleLimit = Math.min(elements.length, 1500);

    for (let i = 0; i < sampleLimit; i++) {
      const styles = getComputedStyle(elements[i]);

      // Shadows
      const shadow = styles.boxShadow;
      if (shadow && shadow !== 'none') {
        if (!shadowMap[shadow]) {
          shadowMap[shadow] = { value: shadow, frequency: 0 };
        }
        shadowMap[shadow].frequency++;
      }

      // Borders
      const borderWidth = styles.borderWidth;
      if (borderWidth && borderWidth !== '0px') {
        const allZero = borderWidth.split(' ').every(v => v === '0px');
        if (!allZero) {
          const key = styles.borderWidth + ' ' + styles.borderStyle + ' ' + styles.borderColor;
          if (!borderMap[key]) {
            borderMap[key] = {
              width: styles.borderWidth,
              style: styles.borderStyle,
              color: styles.borderColor,
              radius: styles.borderRadius,
              frequency: 0
            };
          }
          borderMap[key].frequency++;
        }
      }
    }

    const shadows = Object.values(shadowMap)
      .sort((a, b) => b.frequency - a.frequency)
      .slice(0, 10);

    const borders = Object.values(borderMap)
      .sort((a, b) => b.frequency - a.frequency)
      .slice(0, 10);

    return JSON.stringify({
      shadows: { count: shadows.length, values: shadows },
      borders: { count: borders.length, values: borders }
    });
  } catch (e) {
    return JSON.stringify({
      shadows: { count: 0, values: [] },
      borders: { count: 0, values: [] },
      error: e.message
    });
  }
})()
