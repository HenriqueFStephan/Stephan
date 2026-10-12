import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { I18nService, TranslatePipe } from '../../core/i18n';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, TranslatePipe],
  template: `
    <header>
      <a routerLink="/" fragment="topo" class="brand" aria-label="Stephan">
        <img src="assets/brand/stephan-lockup.png" alt="Stephan" />
      </a>
      <nav>
        <a routerLink="/contato">{{ 'nav.contact' | t }}</a>
        <a routerLink="/abordagem">{{ 'nav.register' | t }}</a>
        <a routerLink="/empresa">{{ 'nav.login' | t }}</a>
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
