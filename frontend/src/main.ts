import { registerLocaleData } from '@angular/common';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import localeEn from '@angular/common/locales/en';
import localePt from '@angular/common/locales/pt';
import { LOCALE_ID } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';

import { AppComponent } from './app/app.component';
import { routes } from './app/app.routes';
import { utf8RepairInterceptor } from './app/core/utf8-repair.interceptor';

registerLocaleData(localePt, 'pt-BR');
registerLocaleData(localeEn, 'en');

bootstrapApplication(AppComponent, {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptors([utf8RepairInterceptor])),
    { provide: LOCALE_ID, useValue: 'pt-BR' },
  ],
}).catch((err) => console.error(err));
