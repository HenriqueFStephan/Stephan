import { Component } from '@angular/core';

import { I18nService, TranslatePipe } from '../../core/i18n';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [TranslatePipe],
  template: `
    <header>
      <a href="#topo" class="brand" aria-label="Stephan">
        <img src="assets/brand/stephan-lockup.png" alt="Stephan" />
      </a>
      <nav>
        <a href="#fazemos">{{ 'nav.work' | t }}</a>
        <a href="#investigamos">{{ 'nav.method' | t }}</a>
        <a href="#socios">{{ 'nav.people' | t }}</a>
        <a href="#contato">{{ 'nav.contact' | t }}</a>
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
