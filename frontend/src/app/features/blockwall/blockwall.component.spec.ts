import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { I18nService } from '../../core/i18n';
import { BlockwallComponent } from './blockwall.component';

const PASSAGE_KEY = 'stephan-blockwall';

describe('BlockwallComponent', () => {
  let fixture: ComponentFixture<BlockwallComponent>;
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    localStorage.removeItem(PASSAGE_KEY);
    api = jasmine.createSpyObj<ApiService>('ApiService', [
      'getBlockwall',
      'unlockBlockwall',
      'resumeBlockwall',
    ]);
    api.getBlockwall.and.returnValue(of({ enabled: true }));

    await TestBed.configureTestingModule({
      imports: [BlockwallComponent],
      providers: [{ provide: ApiService, useValue: api }],
    }).compileComponents();

    TestBed.inject(I18nService).setLang('pt-BR');
  });

  function create(): BlockwallComponent {
    fixture = TestBed.createComponent(BlockwallComponent);
    const component = fixture.componentInstance;
    return component;
  }

  it('shows the maintenance page while the wall is on', () => {
    create();
    fixture.detectChanges();
    const title = (fixture.nativeElement as HTMLElement).querySelector('h1');
    expect(title?.textContent?.trim()).toBe('Site em manutenção');
  });

  it('opens the site when the wall is not configured', () => {
    api.getBlockwall.and.returnValue(of({ enabled: false }));
    const component = create();
    let cleared = false;
    component.cleared.subscribe(() => (cleared = true));
    fixture.detectChanges();
    expect(cleared).toBeTrue();
  });

  it('rejects a wrong password', () => {
    api.unlockBlockwall.and.returnValue(
      throwError(() => new HttpErrorResponse({ status: 401 })),
    );
    const component = create();
    fixture.detectChanges();
    component.password = 'nope';
    component.unlock();
    fixture.detectChanges();
    const alert = (fixture.nativeElement as HTMLElement).querySelector('[role="alert"]');
    expect(alert?.textContent?.trim()).toBe('Senha incorreta.');
    expect(localStorage.getItem(PASSAGE_KEY)).toBeNull();
  });

  it('stores a clearance and opens the site after the right password', () => {
    api.unlockBlockwall.and.returnValue(of({ success: true, passage: 'clearance' }));
    const component = create();
    fixture.detectChanges();
    let cleared = false;
    component.cleared.subscribe(() => (cleared = true));
    component.password = 'secret';
    component.unlock();
    expect(localStorage.getItem(PASSAGE_KEY)).toBe('clearance');
    expect(cleared).toBeTrue();
    expect(component.password).toBe('');
  });

  it('reopens a browser that already holds a clearance', () => {
    localStorage.setItem(PASSAGE_KEY, 'clearance');
    api.resumeBlockwall.and.returnValue(of({ success: true }));
    const component = create();
    let cleared = false;
    component.cleared.subscribe(() => (cleared = true));
    fixture.detectChanges();
    expect(api.resumeBlockwall).toHaveBeenCalledWith('clearance');
    expect(cleared).toBeTrue();
  });
});
