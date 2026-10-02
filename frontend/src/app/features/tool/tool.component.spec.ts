import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';

import { I18nService } from '../../core/i18n';
import { ToolComponent } from './tool.component';

describe('ToolComponent', () => {
  let fixture: ComponentFixture<ToolComponent>;

  beforeEach(async () => {
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
