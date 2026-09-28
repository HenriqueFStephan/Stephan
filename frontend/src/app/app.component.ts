import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';

import { I18nService } from './core/i18n';
import { BlockwallComponent } from './features/blockwall/blockwall.component';
import { FooterComponent } from './shared/footer/footer.component';
import { HeaderComponent } from './shared/header/header.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, HeaderComponent, FooterComponent, BlockwallComponent],
  template: `
    <app-blockwall *ngIf="!open" (cleared)="open = true" />
    <ng-container *ngIf="open">
      <ng-container *ngIf="bare; else site">
        <router-outlet />
      </ng-container>
      <ng-template #site>
        <app-header />
        <main>
          <router-outlet />
        </main>
        <app-footer />
      </ng-template>
    </ng-container>
  `,
  styles: [`
    main {
      min-height: calc(100vh - 140px);
    }
  `],
})
export class AppComponent {
  bare = false;
  open = false;

  constructor(router: Router, _i18n: I18nService) {
    const sync = (): void => {
      const routed = router.url.split('?')[0].split('#')[0].replace(/\/+$/, '');
      const here =
        typeof location !== 'undefined'
          ? location.pathname.split('?')[0].replace(/\/+$/, '')
          : '';
      this.bare =
        routed === '/studio' ||
        here === '/studio' ||
        routed === '/tool' ||
        here === '/tool' ||
        routed === '/empresa' ||
        here === '/empresa';
    };
    router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe(sync);
    sync();
  }
}
