import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
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
      'getCompanyInvitations',
      'retryCompanyInvitations',
      'sendCompanyInvitations',
    ]);
    api.getCompanyInvitations.and.returnValue(
      of({
        round_label: 'rodada-1',
        invited: 10,
        responded_percent: 40,
        waiting_percent: 60,
        unsent: [],
      }),
    );
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
      providers: [provideRouter([]), { provide: ApiService, useValue: api }],
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

  it('shows payment before the list goes out, and a skip only for the admin company', () => {
    api.loginCompany.and.returnValue(
      of({ success: true, passage: 'clearance', company_name: 'Uso interno', company_slug: 'internal' }),
    );
    const component = create();
    fixture.detectChanges();
    component.username = 'admin';
    component.password = 'secret';
    component.login();
    component.preview = {
      forms: 2,
      unit_cents: 1000,
      total_cents: 2000,
      provisional: true,
      methods: ['pix', 'boleto'],
      ignored_empty: 0,
      duplicates_in_file: [],
      already_invited: [],
      invalid: [],
    };
    fixture.detectChanges();

    const root = fixture.nativeElement as HTMLElement;
    const confirm = Array.from(root.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Confirmar pagamento e salvar a lista'),
    ) as HTMLButtonElement;
    expect(confirm.disabled).toBeTrue();
    expect(root.textContent).toContain('Pular pagamento e salvar a lista');
    expect(root.textContent).toContain('R$ 10 por formulário. Este valor não é o preço final.');
    expect(root.textContent).toContain('Pix');

    component.companySlug = 'hse-it';
    fixture.detectChanges();
    expect(root.textContent).not.toContain('Pular pagamento e salvar a lista');
    expect(root.textContent).toContain('Confirmar pagamento e salvar a lista');
  });

  describe('sending the video and the form', () => {
    function signIn(held: number): CompanyComponent {
      api.loginCompany.and.returnValue(
        of({ success: true, passage: 'clearance', company_name: 'Uso interno', company_slug: 'internal' }),
      );
      api.getCompanyInvitations.and.returnValue(
        of({
          round_label: 'rodada-1',
          invited: 0,
          responded_percent: null,
          waiting_percent: null,
          unsent: [],
          held,
          scheduled: [],
          video_ready: true,
        }),
      );
      const component = create();
      fixture.detectChanges();
      component.username = 'admin';
      component.password = 'secret';
      component.login();
      fixture.detectChanges();
      return component;
    }

    function inDays(days: number): string {
      const when = new Date(Date.now() + days * 24 * 3600 * 1000);
      const pad = (value: number) => String(value).padStart(2, '0');
      return `${when.getFullYear()}-${pad(when.getMonth() + 1)}-${pad(when.getDate())}T10:00`;
    }

    function pick(label: string): HTMLButtonElement {
      const root = fixture.nativeElement as HTMLElement;
      return Array.from(root.querySelectorAll('button')).find((button) =>
        button.textContent?.includes(label),
      ) as HTMLButtonElement;
    }

    it('offers nothing to send until a list has been saved', () => {
      signIn(0);
      expect((fixture.nativeElement as HTMLElement).querySelector('#send-block')).toBeNull();
    });

    it('opens the choice from the button and sends at once', () => {
      api.sendCompanyInvitations.and.returnValue(
        of({ people: 3, video_at: '2026-11-26T12:00:00Z', form_at: '2026-11-26T12:01:00Z', immediate: true }),
      );
      const component = signIn(3);
      const root = fixture.nativeElement as HTMLElement;
      expect(root.textContent).toContain('Pessoas aguardando o envio: 3.');
      expect(root.textContent).not.toContain('Confirmar o envio');

      pick('Enviar formulários').click();
      fixture.detectChanges();
      expect(root.textContent).toContain('Enviar o vídeo e o formulário agora');
      expect(root.textContent).toContain('Programar o envio');

      component.confirmSend();
      fixture.detectChanges();
      expect(api.sendCompanyInvitations).toHaveBeenCalledWith('clearance', { mode: 'now' });
      expect(root.textContent).toContain('O vídeo sai agora e o formulário logo depois, para 3 pessoas.');
    });

    it('sends one time for both when they go together', () => {
      api.sendCompanyInvitations.and.returnValue(
        of({ people: 2, video_at: '2030-01-10T09:00:00Z', form_at: '2030-01-10T09:00:00Z', immediate: false }),
      );
      const component = signIn(2);
      component.openSend();
      component.sendMode = 'schedule';
      component.videoAt = inDays(10);
      component.confirmSend();

      const request = api.sendCompanyInvitations.calls.mostRecent().args[1];
      expect(request.mode).toBe('schedule');
      expect(request.video_at).toBe(new Date(inDays(10)).toISOString());
      expect(request.form_at).toBe(request.video_at);
    });

    it('lets the video go days before the form, and never the other way round', () => {
      api.sendCompanyInvitations.and.returnValue(
        of({ people: 2, video_at: '2030-01-05T09:00:00Z', form_at: '2030-01-10T09:00:00Z', immediate: false }),
      );
      const component = signIn(2);
      component.openSend();
      component.sendMode = 'schedule';
      component.sendTogether = false;

      component.videoAt = inDays(10);
      component.formAt = inDays(5);
      expect(component.sendProblem()).toBe('company.sendFormBefore');
      component.confirmSend();
      expect(api.sendCompanyInvitations).not.toHaveBeenCalled();
      expect(component.sendErrorKey).toBe('company.sendFormBefore');

      component.videoAt = inDays(5);
      component.formAt = inDays(10);
      expect(component.sendProblem()).toBe('');
      component.confirmSend();
      expect(api.sendCompanyInvitations).toHaveBeenCalledTimes(1);
    });

    it('asks for a time and refuses one that has passed', () => {
      const component = signIn(2);
      component.openSend();
      component.sendMode = 'schedule';
      expect(component.sendProblem()).toBe('company.sendNeedVideo');
      component.videoAt = '2020-01-01T09:00';
      expect(component.sendProblem()).toBe('company.sendPast');
      component.videoAt = '2099-01-01T09:00';
      expect(component.sendProblem()).toBe('company.sendTooFar');
    });

    it('explains a missing video instead of failing silently', () => {
      api.sendCompanyInvitations.and.returnValue(
        throwError(
          () => new HttpErrorResponse({ status: 503, error: { detail: { code: 'video_not_configured' } } }),
        ),
      );
      const component = signIn(2);
      component.openSend();
      component.confirmSend();
      fixture.detectChanges();
      expect((fixture.nativeElement as HTMLElement).textContent).toContain(
        'O vídeo de apresentação ainda não está no servidor. Nada foi programado.',
      );
      expect(component.sending).toBeFalse();
    });

    it('lists what is already scheduled', () => {
      api.loginCompany.and.returnValue(
        of({ success: true, passage: 'clearance', company_name: 'Uso interno', company_slug: 'internal' }),
      );
      api.getCompanyInvitations.and.returnValue(
        of({
          round_label: 'rodada-1',
          invited: 0,
          responded_percent: null,
          waiting_percent: null,
          unsent: [],
          held: 0,
          scheduled: [{ video_at: '2099-01-05T12:00:00Z', form_at: '2099-01-10T12:00:00Z', people: 4 }],
          video_ready: true,
        }),
      );
      const component = create();
      fixture.detectChanges();
      component.username = 'admin';
      component.password = 'secret';
      component.login();
      fixture.detectChanges();
      const root = fixture.nativeElement as HTMLElement;
      expect(root.textContent).toContain('Envios programados');
      expect(root.textContent).toContain('4 pessoas. Vídeo:');
    });
  });
});
