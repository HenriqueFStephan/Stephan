import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { I18nService } from '../../core/i18n';
import { PasswordComponent } from './password.component';

describe('PasswordComponent', () => {
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['forgotPassword', 'resetPassword']);
    await TestBed.configureTestingModule({
      imports: [PasswordComponent],
      providers: [
        provideRouter([{ path: 'senha', component: PasswordComponent }]),
        { provide: ApiService, useValue: api },
      ],
    }).compileComponents();
    TestBed.inject(I18nService).setLang('pt-BR');
  });

  async function open(url: string): Promise<{ harness: RouterTestingHarness; component: PasswordComponent }> {
    const harness = await RouterTestingHarness.create();
    const component = await harness.navigateByUrl(url, PasswordComponent);
    harness.detectChanges();
    return { harness, component: component! };
  }

  it('asks for the access email and then points to login', async () => {
    const { harness, component } = await open('/senha');
    const root = harness.routeNativeElement;
    expect(root.querySelector('h1')?.textContent).toContain('Esqueci a senha');
    api.forgotPassword.and.returnValue(of({ success: true }));
    component.email = 'pessoa@example.com';
    component.request();
    harness.detectChanges();
    expect(api.forgotPassword).toHaveBeenCalledWith('pessoa@example.com');
    expect(root.textContent).toContain('Veja o e-mail');
    expect(root.querySelector('a.button')?.getAttribute('href')).toBe('/empresa');
  });

  it('saves a new password from the link and returns to login', async () => {
    const { harness, component } = await open('/senha?t=token-senha');
    const root = harness.routeNativeElement;
    expect(root.querySelector('h1')?.textContent).toContain('Nova senha');
    api.resetPassword.and.returnValue(of({ success: true }));
    component.password = 'senha-nova-123';
    component.passwordAgain = 'senha-nova-123';
    component.save();
    harness.detectChanges();
    expect(api.resetPassword).toHaveBeenCalledWith('token-senha', 'senha-nova-123');
    expect(root.textContent).toContain('Senha atualizada');
    expect(root.querySelector('a.button')?.getAttribute('href')).toBe('/empresa');
  });
});
