(() => {
  try {
    const properties = {};
    const root = document.documentElement;
    const rootStyles = getComputedStyle(root);

    // Step 1 (AUTHORITATIVE): Computed custom properties from :root
    // getComputedStyle reflects the cascade winner — this is the ground truth
    for (let i = 0; i < rootStyles.length; i++) {
      const prop = rootStyles[i];
      if (prop.startsWith('--')) {
        const computedValue = rootStyles.getPropertyValue(prop).trim();
        if (computedValue) {
          properties[prop] = {
            value: computedValue,
            source: ':root (computed)',
            resolvedValue: computedValue // same unless overridden by Step 2 below
          };
        }
      }
    }

    // Step 2 (ATTRIBUTION): Walk accessible stylesheets for authored values and source selectors
    // Does NOT overwrite the computed value — only adds source attribution and authored form
    for (const sheet of document.styleSheets) {
      try {
        for (const rule of sheet.cssRules || []) {
          if (rule.style) {
            for (let i = 0; i < rule.style.length; i++) {
              const prop = rule.style[i];
              if (prop.startsWith('--')) {
                const authoredValue = rule.style.getPropertyValue(prop).trim();
                if (authoredValue && properties[prop]) {
                  // Add source attribution from stylesheet (last-write-wins for source, since
                  // CSS cascade means the last matching rule in document order is the winner)
                  properties[prop].source = rule.selectorText || ':root';
                  // If authored value contains var() references, preserve it as authoredValue
                  // so downstream can see both the token reference and the resolved value
                  if (authoredValue.includes('var(')) {
                    properties[prop].authoredValue = authoredValue;
                    // resolvedValue stays as the getComputedStyle result (fully resolved)
                  }
                } else if (authoredValue && !properties[prop]) {
                  // Property not on :root computed — scoped to a selector
                  properties[prop] = {
                    value: authoredValue,
                    source: rule.selectorText || ':root',
                    resolvedValue: authoredValue
                  };
                }
              }
            }
          }
        }
      } catch (_) {
        // Cross-origin stylesheet — skip silently
      }
    }

    return JSON.stringify({
      count: Object.keys(properties).length,
      properties: properties
    });
  } catch (e) {
    return JSON.stringify({ count: 0, properties: {}, error: e.message });
  }
})()
