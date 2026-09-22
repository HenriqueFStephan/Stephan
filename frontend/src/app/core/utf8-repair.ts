/**
 * Repair UTF-8 Portuguese that was decoded as Windows-1252 (mojibake).
 *
 * "Regulamentação" misread as cp1252 becomes "RegulamentaÃ§Ã£o".
 * Interpreting those characters as cp1252 bytes and decoding as UTF-8
 * restores the original letters. Correct Unicode is left unchanged.
 */

const MOJIBAKE_HINT = /Ã|Â|â€/;

/** Unicode code points whose cp1252 byte differs from the code point itself. */
const CP1252_REVERSE: Record<number, number> = {
  0x20ac: 0x80, 0x201a: 0x82, 0x0192: 0x83, 0x201e: 0x84,
  0x2026: 0x85, 0x2020: 0x86, 0x2021: 0x87, 0x02c6: 0x88,
  0x2030: 0x89, 0x0160: 0x8a, 0x2039: 0x8b, 0x0152: 0x8c,
  0x017d: 0x8e, 0x2018: 0x91, 0x2019: 0x92, 0x201c: 0x93,
  0x201d: 0x94, 0x2022: 0x95, 0x2013: 0x96, 0x2014: 0x97,
  0x02dc: 0x98, 0x2122: 0x99, 0x0161: 0x9a, 0x203a: 0x9b,
  0x0153: 0x9c, 0x017e: 0x9e, 0x0178: 0x9f,
};

function toCp1252Bytes(text: string): Uint8Array | null {
  const bytes = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i++) {
    const code = text.charCodeAt(i);
    if (code <= 0xff) {
      bytes[i] = code;
      continue;
    }
    const mapped = CP1252_REVERSE[code];
    if (mapped === undefined) {
      return null;
    }
    bytes[i] = mapped;
  }
  return bytes;
}

export function repairMojibakeText(value: string): string {
  if (!value || !MOJIBAKE_HINT.test(value)) {
    return value;
  }
  const bytes = toCp1252Bytes(value);
  if (!bytes) {
    return value;
  }
  try {
    const repaired = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    return repaired || value;
  } catch {
    return value;
  }
}

export function repairMojibake(value: unknown): unknown {
  if (typeof value === 'string') {
    return repairMojibakeText(value);
  }
  if (Array.isArray(value)) {
    return value.map(repairMojibake);
  }
  if (value && typeof value === 'object' && !(value instanceof Blob) && !(value instanceof ArrayBuffer)) {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, item]) => [key, repairMojibake(item)]),
    );
  }
  return value;
}
