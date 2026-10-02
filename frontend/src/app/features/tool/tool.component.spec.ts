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

  it('opens on the introduction and then the first HSE item', () => {
    const text = (): string => fixture.nativeElement.textContent as string;
    expect(text()).toContain('Indicador das condições de trabalho');
    expect(text()).not.toContain('Sei com clareza');

    const start = fixture.nativeElement.querySelector('.button') as HTMLButtonElement;
    start.click();
    fixture.detectChanges();

    expect(text()).toContain('1 de 35');
    expect(text()).toContain('Sei com clareza o que esperam de mim no trabalho.');
    expect(text()).toContain('Nunca');
  });

  it('advances after a choice and can step back', fakeAsync(() => {
    const start = fixture.nativeElement.querySelector('.button') as HTMLButtonElement;
    start.click();
    fixture.detectChanges();

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
