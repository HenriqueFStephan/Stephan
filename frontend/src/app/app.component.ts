import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';

import { I18nService } from './core/i18n';
import { FooterComponent } from './shared/footer/footer.component';
import { HeaderComponent } from './shared/header/header.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, HeaderComponent, FooterComponent],
  template: `
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
  `,
  styles: [`
    main {
      min-height: calc(100vh - 140px);
    }
  `],
})
export class AppComponent {
  bare = false;

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
        here === '/tool';
    };
    router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe(sync);
    sync();
  }
}
