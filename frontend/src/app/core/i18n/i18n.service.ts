import { Injectable, signal } from '@angular/core';

import { dictionaries, MsgKey } from './messages';

export type Lang = 'pt-BR' | 'en';

const STORAGE_KEY = 'stephan-lang';

function readStoredLang(): Lang {
  if (typeof localStorage === 'undefined') {
    return 'pt-BR';
  }
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'en' || stored === 'pt-BR' ? stored : 'pt-BR';
}

@Injectable({ providedIn: 'root' })
export class I18nService {
  readonly lang = signal<Lang>(readStoredLang());

  constructor() {
    this.applyDocument(this.lang());
  }

  t(key: MsgKey | string, params?: Record<string, string | number>): string {
    const dict = dictionaries[this.lang()] as Record<string, string>;
    const fallback = dictionaries['pt-BR'] as Record<string, string>;
    let value = dict[key] ?? fallback[key] ?? key;
    if (params) {
      for (const [name, raw] of Object.entries(params)) {
        value = value.split(`{{${name}}}`).join(String(raw));
      }
    }
    return value;
  }

  setLang(lang: Lang): void {
    if (lang === this.lang()) {
      return;
    }
    this.lang.set(lang);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, lang);
    }
    this.applyDocument(lang);
  }

  private applyDocument(lang: Lang): void {
    if (typeof document === 'undefined') {
      return;
    }
    document.documentElement.lang = lang;
    document.title = dictionaries[lang]['meta.title'];
    const meta = document.querySelector('meta[name="description"]');
    if (meta) {
      meta.setAttribute('content', dictionaries[lang]['meta.description']);
    }
  }
}
