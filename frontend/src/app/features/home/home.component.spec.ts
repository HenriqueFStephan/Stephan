import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { I18nService } from '../../core/i18n';
import { HomeComponent } from './home.component';

describe('HomeComponent', () => {
  let fixture: ComponentFixture<HomeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HomeComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    TestBed.inject(I18nService).setLang('pt-BR');
    fixture = TestBed.createComponent(HomeComponent);
    fixture.detectChanges();
  });

  it('sends the approach button to the plans page', () => {
    const link = (fixture.nativeElement as HTMLElement).querySelector('.hero a.button');
    expect(link?.getAttribute('href')).toBe('/abordagem');
  });

  it('shows the Portuguese hero title', () => {
    const h1 = (fixture.nativeElement as HTMLElement).querySelector('h1');
    expect(h1?.textContent?.trim()).toBe('meus cabelos peludos');
  });

  it('renders the investigation as form, report, and follow-up', () => {
    const root = fixture.nativeElement as HTMLElement;
    const segments = root.querySelectorAll('#investigamos .thread__segment');
    expect(segments.length).toBe(3);

    const titles = Array.from(root.querySelectorAll('#investigamos .thread__copy h3')).map((node) =>
      node.textContent?.trim(),
    );
    expect(titles).toEqual(['HSE-IT', 'Observação', 'Follow-up']);

    const sources = Array.from(root.querySelectorAll('#investigamos .thread__figure img')).map((img) =>
      img.getAttribute('src'),
    );
    expect(sources).toEqual([
      'assets/method/method-hse.svg',
      'assets/method/method-observe.svg',
      'assets/method/method-follow.svg',
    ]);

    expect(root.querySelector('.thread__segment--text-first')).not.toBeNull();
    expect(root.querySelector('.thread__segment--image-first')).not.toBeNull();
  });

  it('leaves the people and contact sections off the home page', () => {
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('#socios')).toBeNull();
    expect(root.querySelector('#contato')).toBeNull();
    expect(root.querySelector('form')).toBeNull();
  });
});
