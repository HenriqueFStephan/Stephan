import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { I18nService } from '../../core/i18n';
import { isLocalStudioHost, StudioComponent } from './studio.component';

describe('StudioComponent', () => {
  let fixture: ComponentFixture<StudioComponent>;
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    sessionStorage.removeItem('stephan-studio-token');
    api = jasmine.createSpyObj<ApiService>('ApiService', [
      'getStudioStatus',
      'unlockStudio',
      'submitStudioIssue',
    ]);
    api.getStudioStatus.and.returnValue(of({ configured: false, missing: ['STUDIO_ACCESS_TOKEN'] }));
    api.unlockStudio.and.returnValue(of({ success: true, message: 'ok' }));

    await TestBed.configureTestingModule({
      imports: [StudioComponent],
      providers: [{ provide: ApiService, useValue: api }],
    }).compileComponents();

    TestBed.inject(I18nService).setLang('pt-BR');
    fixture = TestBed.createComponent(StudioComponent);
    fixture.detectChanges();
  });

  afterEach(() => {
    sessionStorage.removeItem('stephan-studio-token');
  });

  it('treats loopback hosts as local studio', () => {
    expect(isLocalStudioHost('localhost')).toBeTrue();
    expect(isLocalStudioHost('127.0.0.1')).toBeTrue();
    expect(isLocalStudioHost('::1')).toBeTrue();
    expect(isLocalStudioHost('stephan-psico.netlify.app')).toBeFalse();
  });

  it('opens the composer on localhost without a token', () => {
    expect(isLocalStudioHost(window.location.hostname)).toBeTrue();
    expect(fixture.nativeElement.querySelector('.studio-gate')).toBeNull();
    expect(api.unlockStudio).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('.studio-panel')).toBeTruthy();
    const buttons = Array.from(
      fixture.nativeElement.querySelectorAll('.studio-btn'),
    ) as HTMLButtonElement[];
    expect(buttons.map((btn) => btn.textContent?.trim())).toEqual([
      'Recortar',
      'Imagem',
      'Limpar',
      'Enviar',
    ]);
  });
});
