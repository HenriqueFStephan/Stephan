import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { of, throwError } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { I18nService } from '../../core/i18n';
import { ConfirmComponent } from './confirm.component';

describe('ConfirmComponent', () => {
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['confirmAccount', 'resendConfirmation']);
    await TestBed.configureTestingModule({
      imports: [ConfirmComponent],
      providers: [
        provideRouter([{ path: 'confirmar', component: ConfirmComponent }]),
        { provide: ApiService, useValue: api },
      ],
    }).compileComponents();
    TestBed.inject(I18nService).setLang('pt-BR');
  });

  async function open(url: string): Promise<HTMLElement> {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl(url, ConfirmComponent);
    harness.detectChanges();
    return harness.routeNativeElement;
  }

  it('asks for the email when the link has no token', async () => {
    const root = await open('/confirmar');
    expect(root.querySelector('h1')?.textContent).toContain('Confirme o cadastro');
    expect(root.textContent).toContain('Abra o link');
    expect(api.confirmAccount).not.toHaveBeenCalled();
  });

  it('opens the account and points to login', async () => {
    api.confirmAccount.and.returnValue(of({ success: true }));
    const root = await open('/confirmar?t=token-confirma');
    expect(api.confirmAccount).toHaveBeenCalledWith('token-confirma');
    expect(root.textContent).toContain('E-mail confirmado');
    expect(root.querySelector('a.button')?.getAttribute('href')).toBe('/empresa');
  });

  it('offers another email when the link is no longer valid', async () => {
    api.confirmAccount.and.returnValue(throwError(() => new HttpErrorResponse({ status: 400 })));
    const root = await open('/confirmar?t=token-velho');
    expect(root.textContent).toContain('Este link não confirma');
  });
});
