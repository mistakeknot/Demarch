(() => {
  try {
    const componentMap = {};
    const elements = document.querySelectorAll('body *');

    for (const el of elements) {
      const role = el.getAttribute('role') || el.tagName.toLowerCase();
      const classes = Array.from(el.classList);
      if (classes.length === 0) continue;

      // Use the first meaningful class as the component identifier
      const primaryClass = classes[0];
      const key = role + ':' + primaryClass;

      if (!componentMap[key]) {
        componentMap[key] = {
          name: primaryClass,
          selector: '.' + primaryClass,
          role: role,
          frequency: 0,
          variants: new Set(),
          dataAttributes: new Set()
        };
      }
      componentMap[key].frequency++;

      // Track variant classes (2nd+ classes)
      for (let i = 1; i < classes.length && componentMap[key].variants.size < 10; i++) {
        componentMap[key].variants.add(classes[i]);
      }

      // Track data attributes
      for (const attr of el.attributes) {
        if (attr.name.startsWith('data-') && componentMap[key].dataAttributes.size < 5) {
          componentMap[key].dataAttributes.add(attr.name);
        }
      }
    }

    // Filter: only components that appear 2+ times (repeated patterns)
    // Sort by frequency, cap at 50
    const sorted = Object.values(componentMap)
      .filter(c => c.frequency >= 2)
      .sort((a, b) => b.frequency - a.frequency)
      .slice(0, 50)
      .map(c => ({
        name: c.name,
        selector: c.selector,
        role: c.role,
        frequency: c.frequency,
        variants: Array.from(c.variants),
        dataAttributes: Array.from(c.dataAttributes)
      }));

    return JSON.stringify({ count: sorted.length, components: sorted });
  } catch (e) {
    return JSON.stringify({ count: 0, components: [], error: e.message });
  }
})()
