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

  it('opens on the consent page, then the first HSE item', () => {
    const text = (): string => fixture.nativeElement.textContent as string;
    expect(text()).toContain('Avaliação de fatores psicossociais no trabalho');
    expect(text()).toContain('Participação voluntária');
    expect(text()).toContain('Li e concordo em participar da avaliação nas condições acima.');
    expect(text()).toContain('renatasobral@stephan.net.br');
    expect(text()).not.toContain('Indicador das condições de trabalho');
    expect(text()).not.toContain('Sei com clareza');

    const next = fixture.nativeElement.querySelector('.button') as HTMLButtonElement;
    expect(next.disabled).toBeTrue();
    next.click();
    fixture.detectChanges();
    expect(text()).toContain('Participação voluntária');

    const box = fixture.nativeElement.querySelector('input[type="checkbox"]') as HTMLInputElement;
    box.click();
    fixture.detectChanges();
    expect(next.disabled).toBeFalse();
    next.click();
    fixture.detectChanges();

    expect(text()).toContain('1 de 35');
    expect(text()).toContain('Sei claramente o que é esperado de mim no trabalho.');
    expect(text()).toContain('Nunca');
    expect(text()).not.toContain('Questionário sociodemográfico e ocupacional');
    expect(text()).not.toContain('Trinta e cinco perguntas');
    expect(text()).not.toContain('Faixa Etária');
    expect(fixture.nativeElement.querySelector('.choice__n')).toBeNull();

    const back = fixture.nativeElement.querySelector('.text') as HTMLButtonElement;
    back.click();
    fixture.detectChanges();
    expect(text()).toContain('Li e concordo em participar da avaliação nas condições acima.');
    expect(text()).not.toContain('Faixa Etária');
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

  it('names the company on the consent page and waits for agreement', () => {
    const opened = http.expectOne('http://localhost:8000/api/v1/tool/access');
    opened.flush({ state: 'ready', company_name: 'Oficina Ltda', draft: null });
    fixture.detectChanges();

    const text = (): string => fixture.nativeElement.textContent as string;
    expect(text()).toContain('Avaliação de fatores psicossociais no trabalho — Oficina Ltda');
    expect(text()).toContain('A Oficina Ltda contratou a Stephan');
    expect(text()).not.toContain('Sei com clareza');

    const next = fixture.nativeElement.querySelector('.button') as HTMLButtonElement;
    expect(next.disabled).toBeTrue();
    const box = fixture.nativeElement.querySelector('input[type="checkbox"]') as HTMLInputElement;
    box.click();
    fixture.detectChanges();
    next.click();
    fixture.detectChanges();
    expect(text()).toContain('1 de 35');
    expect(text()).toContain('Sei claramente o que é esperado de mim no trabalho.');
  });

  it('restores a draft on the saved question and can save it again', () => {
    const opened = http.expectOne('http://localhost:8000/api/v1/tool/access');
    const answers = Array(35).fill(null);
    answers[0] = 4;
    answers[1] = 2;
    opened.flush({
      state: 'ready',
      company_name: 'Uso interno',
      draft: {
        place: 'ask',
        index: 2,
        demographics: {
          age_band: '35_44',
          gender: 'female',
          education: 'high_school',
          tenure_org: 'y1_3',
          work_shift: 'day_fixed',
          leadership: 'no',
        },
        answers,
      },
    });
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Continuando de onde você parou.');
    expect(text).toContain('3 de 35');
    expect(text).toContain('No trabalho, diferentes grupos exigem de mim coisas difíceis de conciliar.');
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

function openQuestions(fixture: ComponentFixture<ToolComponent>): void {
  const box = fixture.nativeElement.querySelector('input[type="checkbox"]') as HTMLInputElement;
  box.click();
  fixture.detectChanges();
  const agree = fixture.nativeElement.querySelector('.button') as HTMLButtonElement;
  agree.click();
  fixture.detectChanges();
}
