function fold(char: string): string {
    return char.normalize('NFD').replace(/\p{M}/gu, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase()
}

/**
 * Splits a suggestion name into the part the query matches and the rest, for the bold match of mockup screen 2d.
 * The match is a prefix and ignores case and diacritics, so "hoan kiem" matches "Hoàn Kiếm". The text keeps its
 * own characters, so the diacritics of the backend are never changed.
 */
export function splitMatchedPrefix(text: string, query: string): { matched: string; rest: string } {
    const wanted = Array.from(query.trim()).map(fold).join('')
    if (wanted === '') return { matched: '', rest: text }

    let folded = ''
    let end = 0
    for (const char of text) {
        folded += fold(char)
        end += char.length
        if (!wanted.startsWith(folded)) return { matched: '', rest: text }
        if (folded.length >= wanted.length) return { matched: text.slice(0, end), rest: text.slice(end) }
    }
    return { matched: '', rest: text }
}
