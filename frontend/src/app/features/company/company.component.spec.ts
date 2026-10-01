import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { I18nService } from '../../core/i18n';
import { CompanyOverview } from '../../core/models';
import { CompanyComponent } from './company.component';

const PASSAGE_KEY = 'stephan-company-passage';

const overview: CompanyOverview = {
  source: 'simulated',
  company_id: 'demo',
  respondent_count: 100,
  first_response_on: '2026-08-03',
  latest_response_on: '2026-09-26',
  alpha: [
    { id: 'overall', alpha: 0.917, items: 35, n: 100, reading: 'excellent', mean: null },
    { id: 'demands', alpha: 0.941, items: 8, n: 100, reading: 'excellent', mean: 2.98 },
  ],
  dimensions: [{ id: 'demands', mean: 2.98 }],
  sectors: [{ id: 'operation', count: 34, means: [{ id: 'demands', mean: 2.7 }] }],
  weeks: [{ week: '2026-09-21', count: 9 }],
  bands: [{ id: 'demands', urgent: 40, improve: 30, good: 20, maintain: 10 }],
};

describe('CompanyComponent', () => {
  let fixture: ComponentFixture<CompanyComponent>;
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(async () => {
    sessionStorage.removeItem(PASSAGE_KEY);
    api = jasmine.createSpyObj<ApiService>('ApiService', [
      'loginCompany',
      'getCompanyOverview',
      'getCompanyInvitations',
    ]);
    api.getCompanyInvitations.and.returnValue(
      of({ round_label: 'rodada-1', invited: 0, responded_percent: null, waiting_percent: null }),
    );

    await TestBed.configureTestingModule({
      imports: [CompanyComponent],
      providers: [{ provide: ApiService, useValue: api }],
    }).compileComponents();

    TestBed.inject(I18nService).setLang('pt-BR');
  });

  function create(): CompanyComponent {
    fixture = TestBed.createComponent(CompanyComponent);
    return fixture.componentInstance;
  }

  it('shows the company login', () => {
    create();
    fixture.detectChanges();
    const title = (fixture.nativeElement as HTMLElement).querySelector('h1');
    expect(title?.textContent?.trim()).toBe('Leitura da organização');
  });

  it('rejects a wrong password', () => {
    api.loginCompany.and.returnValue(throwError(() => new HttpErrorResponse({ status: 401 })));
    const component = create();
    fixture.detectChanges();
    component.username = 'admin';
    component.password = 'nope';
    component.login();
    fixture.detectChanges();
    const alert = (fixture.nativeElement as HTMLElement).querySelector('[role="alert"]');
    expect(alert?.textContent?.trim()).toBe('Usuário ou senha incorretos.');
    expect(sessionStorage.getItem(PASSAGE_KEY)).toBeNull();
  });

  it('shows Cronbach alpha for the latest simulated reading', () => {
    api.loginCompany.and.returnValue(of({ success: true, passage: 'clearance' }));
    api.getCompanyOverview.and.returnValue(of(overview));
    const component = create();
    fixture.detectChanges();
    component.username = 'admin';
    component.password = 'secret';
    component.login();
    fixture.detectChanges();

    const root = fixture.nativeElement as HTMLElement;
    expect(sessionStorage.getItem(PASSAGE_KEY)).toBe('clearance');
    expect(component.password).toBe('');
    expect(root.querySelector('#alpha-title')?.textContent).toContain('Alfa de Cronbach');
    expect(root.querySelector('#invite-title')?.textContent).toContain('Quem recebe o link');
    expect(root.textContent).toContain('0,917');
    expect(root.textContent).toContain('26/09/2026');
    expect(root.textContent).toContain('100 respostas completas');
    expect(root.textContent).toContain('Demonstração');
    expect(root.textContent).toContain('Nesta rodada ainda não há convites.');
    expect(root.textContent).not.toContain('@');
  });
});
