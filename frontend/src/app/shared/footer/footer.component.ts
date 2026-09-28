import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { TranslatePipe } from '../../core/i18n';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [RouterLink, TranslatePipe],
  template: `
    <footer>
      <img src="assets/brand/stephan-word.png" alt="stephan" />
      <a routerLink="/empresa">{{ 'footer.company' | t }}</a>
      <p>{{ 'footer.note' | t }}</p>
    </footer>
  `,
  styleUrls: ['./footer.component.scss'],
})
export class FooterComponent {}
