// Fit only when content or the paper rectangle changes. Hidden reveal items
// retain their layout, so later lines never push the star or card around.
export function fitGreeting(message) {
  const copy = message.querySelector('.letter-copy');
  copy.style.removeProperty('font-size');
  message.classList.remove('compact');
  const fits = () => message.scrollHeight <= message.clientHeight && message.scrollWidth <= message.clientWidth;
  if (fits()) return;
  message.classList.add('compact');
  if (fits()) return;
  let low = 12, high = Math.floor(parseFloat(getComputedStyle(copy).fontSize));
  while (low < high) {
    const size = Math.ceil((low + high) / 2);
    copy.style.fontSize = `${size}px`;
    if (fits()) low = size;
    else high = size - 1;
  }
  copy.style.fontSize = `${low}px`;
}

export function wrapAddress(text, measure, width) {
  let segmenter;
  const lines = [''];
  for (const word of text.trim().split(/\s+/u)) {
    const current = lines.at(-1);
    const joined = current ? `${current} ${word}` : word;
    if (measure(joined) <= width) {
      lines[lines.length - 1] = joined;
      continue;
    }
    if (current) lines.push('');
    if (!segmenter && typeof Intl.Segmenter === 'function') segmenter = new Intl.Segmenter(undefined, {granularity:'grapheme'});
    const glyphs = segmenter ? Array.from(segmenter.segment(word), part=>part.segment) : Array.from(word);
    for (const glyph of glyphs) {
      const line = lines.at(-1);
      if (line && measure(line + glyph) > width) lines.push(glyph);
      else lines[lines.length - 1] = line + glyph;
    }
  }
  return lines;
}
