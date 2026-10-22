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
  days: [{ day: '2026-09-21', count: 9 }],
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
      'getCompanyRounds',
    ]);
    api.getCompanyRounds.and.returnValue(
      of([
        {
          label: 'rodada-1',
          opened_on: '2026-08-03',
          closed_on: null,
          invited: 10,
          responded_percent: 40,
          waiting_percent: 60,
          latest_response_on: null,
        },
      ]),
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

  it('shows round statistics only after the company asks for them', () => {
    api.loginCompany.and.returnValue(
      of({ success: true, passage: 'clearance', company_name: 'Uso interno', company_slug: 'internal' }),
    );
    api.getCompanyOverview.and.returnValue(of({ ...overview, source: 'recorded', company_id: 'internal' }));
    const component = create();
    fixture.detectChanges();
    component.username = 'admin';
    component.password = 'secret';
    component.login();
    fixture.detectChanges();

    const root = fixture.nativeElement as HTMLElement;
    expect(sessionStorage.getItem(PASSAGE_KEY)).toBe('clearance');
    expect(component.password).toBe('');
    expect(api.getCompanyOverview).not.toHaveBeenCalled();
    expect(root.querySelector('#alpha-title')).toBeNull();
    expect(root.querySelector('#weeks-title')).toBeNull();
    expect(root.textContent).not.toContain('100 pessoas');
    expect(root.textContent).not.toContain('Demonstração');
    expect(root.querySelector('#invite-title')?.textContent).toContain('Enviar formulários');
    expect(root.querySelector('#rounds-title')?.textContent).toContain('Rodadas');
    expect(root.textContent).toContain('rodada-1');
    expect(root.textContent).toContain('40%');
    expect(root.textContent).toContain('60%');
    expect(root.textContent).toContain('Aberta');

    const show = Array.from(root.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Ver estatísticas'),
    ) as HTMLButtonElement;
    show.click();
    fixture.detectChanges();

    expect(api.getCompanyOverview).toHaveBeenCalledWith('clearance', 'rodada-1');
    expect(root.querySelector('#alpha-title')?.textContent).toContain('Alfa de Cronbach');
    expect(root.querySelector('#weeks-title')?.textContent).toContain('Formulários recebidos');
    expect(root.textContent).toContain('0,917');
    expect(root.textContent).not.toContain('100 pessoas');
    expect(root.textContent).not.toContain('100 respostas completas');
    expect(root.querySelector('[aria-labelledby="alpha-title"] tbody')?.querySelectorAll('tr').length).toBe(1);
    const expand = Array.from(root.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Ver as escalas'),
    ) as HTMLButtonElement;
    expand.click();
    fixture.detectChanges();
    expect(root.textContent).toContain('26/09/2026');
    expect(root.textContent).toContain('100 respostas completas');
    expect(root.querySelector('[aria-labelledby="alpha-title"] tbody')?.querySelectorAll('tr').length).toBe(2);
    expect(root.textContent).not.toContain('Demonstração');
    expect(root.textContent).not.toContain('Nesta rodada ainda não há convites.');
    expect(root.textContent).not.toContain('@');
    expect(root.querySelector('.meters')).not.toBeNull();
    expect(root.querySelector('.stacks')).toBeNull();
    expect(root.querySelector('.sectors')).toBeNull();

    const sectors = Array.from(root.querySelectorAll('[role="tab"]')).find((tab) =>
      tab.textContent?.includes('Por área'),
    ) as HTMLButtonElement;
    sectors.click();
    fixture.detectChanges();
    expect(root.querySelector('.meters')).toBeNull();
    expect(root.querySelector('.sectors')).not.toBeNull();
    expect(root.querySelector('.file__pick')?.textContent?.trim()).toBe('Escolher arquivo');
    expect(root.querySelector('input[type="file"]')?.classList.contains('file__input')).toBeTrue();
  });

  it('closes statistics and explains a round that nobody has answered', () => {
    api.loginCompany.and.returnValue(
      of({ success: true, passage: 'clearance', company_name: 'Uso interno', company_slug: 'internal' }),
    );
    api.getCompanyOverview.and.returnValue(
      of({ ...overview, source: 'recorded', company_id: 'internal', respondent_count: 0, dimensions: [], sectors: [], bands: [] }),
    );
    const component = create();
    fixture.detectChanges();
    component.username = 'admin';
    component.password = 'secret';
    component.login();
    fixture.detectChanges();

    const root = fixture.nativeElement as HTMLElement;
    const show = Array.from(root.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Ver estatísticas'),
    ) as HTMLButtonElement;
    show.click();
    fixture.detectChanges();

    expect(root.querySelector('#stats-pending-title')?.textContent).toContain('Nenhum formulário respondido');
    expect(root.textContent).toContain('A rodada começou em 03/08/2026, mas nenhum formulário foi respondido.');
    expect(root.querySelector('#weeks-title')).toBeNull();
    expect(root.querySelector('#alpha-title')).toBeNull();
    expect(api.getCompanyOverview).toHaveBeenCalledTimes(1);

    const hide = Array.from(root.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Ocultar estatísticas'),
    ) as HTMLButtonElement;
    hide.click();
    fixture.detectChanges();

    expect(root.querySelector('#stats-pending-title')).toBeNull();
    expect(root.textContent).toContain('Ver estatísticas');
    expect(api.getCompanyOverview).toHaveBeenCalledTimes(1);
  });

  it('keeps statistics open and loads the newly selected round', () => {
    api.getCompanyRounds.and.returnValue(
      of([
        {
          label: '4',
          opened_on: '2026-10-01',
          closed_on: null,
          invited: 2,
          responded_percent: 0,
          waiting_percent: 100,
          latest_response_on: null,
        },
        {
          label: '3',
          opened_on: '2026-09-01',
          closed_on: '2026-09-25',
          invited: 120,
          responded_percent: 70,
          waiting_percent: 30,
          latest_response_on: '2026-09-25',
        },
      ]),
    );
    api.loginCompany.and.returnValue(
      of({ success: true, passage: 'clearance', company_name: 'Uso interno', company_slug: 'internal' }),
    );
    api.getCompanyOverview.and.returnValues(
      of({ ...overview, source: 'recorded', company_id: 'internal' }),
      of({
        ...overview,
        source: 'recorded',
        company_id: 'internal',
        respondent_count: 0,
        dimensions: [],
        sectors: [],
        bands: [],
      }),
    );
    const component = create();
    fixture.detectChanges();
    component.username = 'admin';
    component.password = 'secret';
    component.login();
    fixture.detectChanges();

    const root = fixture.nativeElement as HTMLElement;
    const show = Array.from(root.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Ver estatísticas'),
    ) as HTMLButtonElement;
    show.click();
    fixture.detectChanges();
    expect(root.querySelector('#weeks-title')).not.toBeNull();

    component.onRoundPicked('3');
    fixture.detectChanges();

    expect(api.getCompanyOverview).toHaveBeenCalledWith('clearance', '3');
    expect(root.querySelector('#stats-pending-title')).not.toBeNull();
    expect(root.textContent).toContain('Ocultar estatísticas');
  });
});
