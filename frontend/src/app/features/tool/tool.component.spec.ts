import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';

import { I18nService } from '../../core/i18n';
import { ToolComponent } from './tool.component';

describe('ToolComponent', () => {
  let fixture: ComponentFixture<ToolComponent>;

  beforeEach(async () => {
    window.history.replaceState({}, '', '/tool');
    await TestBed.configureTestingModule({
      imports: [ToolComponent, HttpClientTestingModule],
    }).compileComponents();

    TestBed.inject(I18nService).setLang('pt-BR');
    fixture = TestBed.createComponent(ToolComponent);
    fixture.detectChanges();
  });

  it('opens on the introduction, then the sociodemographic form, then the first HSE item', () => {
    const text = (): string => fixture.nativeElement.textContent as string;
    expect(text()).toContain('Indicador das condições de trabalho');
    expect(text()).not.toContain('Sei com clareza');
    expect(text()).not.toContain('Faixa Etária');

    const start = fixture.nativeElement.querySelector('.button') as HTMLButtonElement;
    start.click();
    fixture.detectChanges();

    expect(text()).toContain('Questionário sociodemográfico e ocupacional');
    expect(text()).toContain('Faixa Etária');
    expect(text()).toContain('Preenchimento obrigatório');
    expect(text()).toContain('Região Sul');
    const next = fixture.nativeElement.querySelector('.button') as HTMLButtonElement;
    expect(next.disabled).toBeTrue();

    markRequired(fixture);
    expect((fixture.nativeElement.querySelector('.button') as HTMLButtonElement).disabled).toBeFalse();
    (fixture.nativeElement.querySelector('.button') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(text()).toContain('1 de 35');
    expect(text()).toContain('Sei com clareza o que esperam de mim no trabalho.');
    expect(text()).toContain('Nunca');

    const back = fixture.nativeElement.querySelector('.text') as HTMLButtonElement;
    back.click();
    fixture.detectChanges();
    expect(text()).toContain('Faixa Etária');
    expect(fixture.componentInstance.profile['age_band']).toBe('18_24');
  });

  it('advances after a choice and can step back', fakeAsync(() => {
    openQuestions(fixture);

    const choice = fixture.nativeElement.querySelector('.choice') as HTMLButtonElement;
    choice.click();
    tick(180);
    fixture.detectChanges();

    expect(fixture.componentInstance.index).toBe(1);
    expect(fixture.nativeElement.textContent).toContain('Posso decidir quando fazer uma pausa.');

    const back = fixture.nativeElement.querySelector('.text') as HTMLButtonElement;
    back.click();
    fixture.detectChanges();
    expect(fixture.componentInstance.index).toBe(0);
  }));
});

describe('ToolComponent campaign draft', () => {
  let fixture: ComponentFixture<ToolComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    window.history.replaceState({}, '', '/tool?t=campaign-token-1');
    await TestBed.configureTestingModule({
      imports: [ToolComponent, HttpClientTestingModule],
    }).compileComponents();
    TestBed.inject(I18nService).setLang('pt-BR');
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(ToolComponent);
    fixture.detectChanges();
  });

  afterEach(() => {
    http.verify();
    window.history.replaceState({}, '', '/tool');
  });

  it('restores a draft on the saved question and can save it again', () => {
    const opened = http.expectOne('http://localhost:8000/api/v1/tool/access');
    const answers = Array(35).fill(null);
    answers[0] = 4;
    answers[1] = 2;
    opened.flush({
      state: 'ready',
      draft: {
        place: 'ask',
        index: 2,
        demographics: { age_band: '35_44', economic_sector: 'health' },
        answers,
      },
    });
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Continuando de onde você parou.');
    expect(text).toContain('3 de 35');
    expect(text).toContain('Grupos diferentes no trabalho me pedem coisas difíceis de conciliar.');
    expect(text).toContain('Salvar e continuar depois');

    const save = [...fixture.nativeElement.querySelectorAll('button')].find((button) =>
      (button.textContent || '').includes('Salvar e continuar depois'),
    ) as HTMLButtonElement;
    save.click();
    const posted = http.expectOne('http://localhost:8000/api/v1/tool/drafts');
    expect(posted.request.body.place).toBe('ask');
    expect(posted.request.body.index).toBe(2);
    expect(posted.request.body.demographics.age_band).toBe('35_44');
    expect(posted.request.body.token).toBe('campaign-token-1');
    posted.flush({ saved: true });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Abra o mesmo link');
  });
});

function markRequired(fixture: ComponentFixture<ToolComponent>): void {
  for (const id of ['age_band', 'economic_sector']) {
    const choice = fixture.nativeElement.querySelector(
      `[data-question="${id}"] .choice`,
    ) as HTMLButtonElement;
    choice.click();
  }
  fixture.detectChanges();
}

function openQuestions(fixture: ComponentFixture<ToolComponent>): void {
  const start = fixture.nativeElement.querySelector('.button') as HTMLButtonElement;
  start.click();
  fixture.detectChanges();
  markRequired(fixture);
  const next = fixture.nativeElement.querySelector('.button') as HTMLButtonElement;
  next.click();
  fixture.detectChanges();
}
