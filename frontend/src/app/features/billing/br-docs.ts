/** Masks and check digits for Brazilian registration numbers. */

export function onlyDigits(value: string): string {
  return value.replace(/\D/g, '');
}

export function maskCnpj(value: string): string {
  const d = onlyDigits(value).slice(0, 14);
  let out = d.slice(0, 2);
  if (d.length > 2) out += '.' + d.slice(2, 5);
  if (d.length > 5) out += '.' + d.slice(5, 8);
  if (d.length > 8) out += '/' + d.slice(8, 12);
  if (d.length > 12) out += '-' + d.slice(12, 14);
  return out;
}

export function maskCpf(value: string): string {
  const d = onlyDigits(value).slice(0, 11);
  let out = d.slice(0, 3);
  if (d.length > 3) out += '.' + d.slice(3, 6);
  if (d.length > 6) out += '.' + d.slice(6, 9);
  if (d.length > 9) out += '-' + d.slice(9, 11);
  return out;
}

export function maskCep(value: string): string {
  const d = onlyDigits(value).slice(0, 8);
  if (d.length <= 5) return d;
  return d.slice(0, 5) + '-' + d.slice(5);
}

export function maskPhone(value: string): string {
  const d = onlyDigits(value).slice(0, 11);
  if (!d.length) return '';
  if (d.length < 3) return '(' + d;
  const area = d.slice(0, 2);
  const rest = d.slice(2);
  if (rest.length <= 4) return `(${area}) ${rest}`;
  if (d.length <= 10) return `(${area}) ${rest.slice(0, 4)}-${rest.slice(4)}`;
  return `(${area}) ${rest.slice(0, 5)}-${rest.slice(5)}`;
}

function checkDigit(base: string, factors: number[]): number {
  const total = base.split('').reduce((sum, digit, index) => sum + Number(digit) * factors[index], 0);
  const rest = total % 11;
  return rest < 2 ? 0 : 11 - rest;
}

export function isCnpj(value: string): boolean {
  const d = onlyDigits(value);
  if (d.length !== 14 || /^(\d)\1+$/.test(d)) return false;
  const first = checkDigit(d.slice(0, 12), [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  const second = checkDigit(d.slice(0, 12) + String(first), [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  return d.endsWith(`${first}${second}`);
}

export function isCpf(value: string): boolean {
  const d = onlyDigits(value);
  if (d.length !== 11 || /^(\d)\1+$/.test(d)) return false;
  const first = checkDigit(d.slice(0, 9), [10, 9, 8, 7, 6, 5, 4, 3, 2]);
  const second = checkDigit(d.slice(0, 9) + String(first), [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]);
  return d.endsWith(`${first}${second}`);
}

export function isEmail(value: string): boolean {
  const email = value.trim();
  const domain = email.split('@')[1] ?? '';
  return email.split('@').length === 2 && domain.includes('.') && !domain.startsWith('.') && !domain.endsWith('.');
}

export function isPhone(value: string): boolean {
  const d = onlyDigits(value);
  return d.length === 10 || d.length === 11;
}

export const BRAZIL_STATES = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
  'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
] as const;
