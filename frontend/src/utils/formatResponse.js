export function formatToBullets(text) {
  if (!text || typeof text !== 'string') return text;
  // Remove leading salutations like "Good Morning", "Hello", etc.
  text = text.replace(/^\s*(?:good\s+morning|good\s+afternoon|good\s+evening|hello|hi|hey)[^\n\.!\?]*[\.!\?]?\s*/i, '');

  // If already contains markdown list markers or headings, normalize and keep as-is
  if (/^\s*[-*+]\s+/m.test(text) || /^\s*\d+\.\s+/m.test(text) || /\n\s*[-*+\d]/.test(text) || /^#{1,6}\s+/m.test(text)) {
    // Normalize '*' markers to '-' and remove stray '**' markers
    text = text.replace(/\n\s*\*+/g, '\n- ').replace(/\*\*/g, '');
    return text;
  }

  // Normalize whitespace and remove stray markdown bold markers
  text = text.replace(/\s+/g, ' ').replace(/\*\*/g, '');

  // If the text contains explicit list separators (asterisks on lines), convert them
  if (/\n\s*\*/.test(text) || /\*\s{2,}/.test(text)) {
    const lines = text.split(/\n|\r/).map(l => l.trim()).filter(Boolean);
    const items = [];
    lines.forEach(l => {
      if (/^\*+\s*/.test(l)) items.push(l.replace(/^\*+\s*/, '- '));
      else items.push('- ' + l.replace(/^[-\s]+/, ''));
    });
    return items.join('\n\n');
  }

  // Split into sentences (simple heuristic). Keep abbreviations naive handling.
  const sentences = text
    .split(/(?<=[.!?])\s+(?=[A-Z0-9])/g)
    .map(s => s.trim())
    .filter(Boolean);

  // If we have multiple sentences (2 or more), convert to bullet list
  if (sentences.length >= 2) {
    return sentences.map(s => `- ${s.replace(/^[-\s]+/, '')}`).join('\n\n');
  }

  // Otherwise return original text
  return text;
}
