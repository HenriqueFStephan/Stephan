import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { I18nService } from '../../core/i18n';
import { HomeComponent } from './home.component';

describe('HomeComponent', () => {
  let fixture: ComponentFixture<HomeComponent>;

  beforeEach(async () => {
    const api = jasmine.createSpyObj<ApiService>('ApiService', ['submitContact']);
    api.submitContact.and.returnValue(of({ ok: true }));

    await TestBed.configureTestingModule({
      imports: [HomeComponent],
      providers: [{ provide: ApiService, useValue: api }],
    }).compileComponents();

    TestBed.inject(I18nService).setLang('pt-BR');
    fixture = TestBed.createComponent(HomeComponent);
    fixture.detectChanges();
  });

  it('renders four method segments with half-width copy and placeholder art', () => {
    const root = fixture.nativeElement as HTMLElement;
    const segments = root.querySelectorAll('#investigamos .thread__segment');
    expect(segments.length).toBe(4);

    segments.forEach((segment) => {
      const copy = segment.querySelector('.thread__copy');
      const figure = segment.querySelector('.thread__figure img');
      expect(copy).withContext('each segment has a copy block').not.toBeNull();
      expect(figure).withContext('each segment has placeholder art').not.toBeNull();
      expect(figure?.getAttribute('src')).toMatch(/^assets\/method\/method-/);
    });

    expect(root.querySelector('.thread__segment--text-first')).not.toBeNull();
    expect(root.querySelector('.thread__segment--image-first')).not.toBeNull();
  });
});
