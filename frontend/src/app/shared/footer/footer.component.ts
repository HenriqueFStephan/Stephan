import { Component } from '@angular/core';

import { TranslatePipe } from '../../core/i18n';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [TranslatePipe],
  template: `
    <footer>
      <img src="assets/brand/stephan-word.png" alt="stephan" />
      <p>{{ 'footer.note' | t }}</p>
    </footer>
  `,
  styleUrls: ['./footer.component.scss'],
})
export class FooterComponent {}
