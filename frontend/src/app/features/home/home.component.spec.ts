import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { I18nService } from '../../core/i18n';
import { HomeComponent, NR1_NORM_PDF_URL } from './home.component';

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

  it('links the method CTA to the method section and contact to /contato', () => {
    const root = fixture.nativeElement as HTMLElement;
    const methodLink = root.querySelector('.hero__actions a.button');
    const contactLink = root.querySelector('.hero__actions a.button--ghost');
    expect(methodLink?.getAttribute('href')).toBe('#metodo');
    expect(contactLink?.getAttribute('href')).toBe('/contato');
  });

  it('shows the Portuguese hero title from issue #12', () => {
    const h1 = (fixture.nativeElement as HTMLElement).querySelector('h1');
    expect(h1?.textContent?.trim()).toBe('Avaliação e gestão de riscos psicossociais');
  });

  it('renders the six content sections from the issue copy', () => {
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('#conceito')).not.toBeNull();
    expect(root.querySelector('#custo')).not.toBeNull();
    expect(root.querySelector('#norma')).not.toBeNull();
    expect(root.querySelector('#metodo')).not.toBeNull();
    expect(root.querySelector('#entregaveis')).not.toBeNull();
    expect(root.querySelector('#privacidade')).not.toBeNull();
    expect(root.querySelector('#proximo-passo')).not.toBeNull();
  });

  it('lists seven HSE dimensions and three method steps', () => {
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelectorAll('#conceito .dimensions li').length).toBe(7);

    const segments = root.querySelectorAll('#metodo .thread__segment');
    expect(segments.length).toBe(3);

    const titles = Array.from(root.querySelectorAll('#metodo .thread__copy h3')).map((node) =>
      node.textContent?.trim(),
    );
    expect(titles).toEqual(['HSE-IT', 'Leitura estatística', 'Grupo focal']);
  });

  it('links NR-1 and norm citations to the official PDF (issue #13)', () => {
    const root = fixture.nativeElement as HTMLElement;
    const normSection = root.querySelector('#norma');
    expect(normSection).not.toBeNull();

    const leadLink = normSection?.querySelector('.intro .norm-link');
    expect(leadLink?.textContent?.trim()).toBe('NR-1');
    expect(leadLink?.getAttribute('href')).toBe(NR1_NORM_PDF_URL);
    expect(leadLink?.getAttribute('target')).toBe('_blank');

    const citeLinks = normSection?.querySelectorAll('.norm .norm-link') ?? [];
    expect(citeLinks.length).toBe(9);
    citeLinks.forEach((anchor) => {
      expect(anchor.getAttribute('href')).toBe(NR1_NORM_PDF_URL);
    });
    expect(citeLinks[0]?.textContent?.trim()).toBe('1.5.3.1.4º');
  });

  it('leaves the people and contact form sections off the home page', () => {
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('#socios')).toBeNull();
    expect(root.querySelector('#contato')).toBeNull();
    expect(root.querySelector('form')).toBeNull();
  });
});
