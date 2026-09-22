import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { I18nService, TranslatePipe } from '../../core/i18n';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, TranslatePipe],
  template: `
    <header>
      <a routerLink="/" class="brand">Sobral Psico</a>
      <nav>
        <a routerLink="/">{{ 'nav.home' | t }}</a>
        <button type="button" (click)="toggleLang()">{{ 'nav.lang' | t }}</button>
      </nav>
    </header>
  `,
  styleUrls: ['./header.component.scss'],
})
export class HeaderComponent {
  constructor(private i18n: I18nService) {}

  toggleLang(): void {
    this.i18n.setLang(this.i18n.lang() === 'pt-BR' ? 'en' : 'pt-BR');
  }
}
