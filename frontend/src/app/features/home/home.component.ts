import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { TranslatePipe } from '../../core/i18n';

/** Canonical NR-1 PDF (chapter 1.5 citations on the home page). */
export const NR1_NORM_PDF_URL =
  'https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/normas-regulamentadora/normas-regulamentadoras-vigentes/nr-01-atualizada-2025-i-3.pdf';

type NormItem = {
  bodyKey: string;
  cites: readonly string[];
};

type MethodStep = {
  index: string;
  image: string;
  layout: 'text-first' | 'image-first';
  titleKey: string;
  bodyKey: string;
};

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslatePipe],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent {
  readonly dimensions = [1, 2, 3, 4, 5, 6, 7] as const;
  readonly stats = [1, 2, 3] as const;
  readonly gains = [1, 2, 3, 4, 5, 6] as const;
  readonly nr1NormPdfUrl = NR1_NORM_PDF_URL;

  readonly normItems: readonly NormItem[] = [
    { bodyKey: 'home.norm.item.1.body', cites: ['1.5.3.1.4º'] },
    { bodyKey: 'home.norm.item.2.body', cites: ['1.5.3.2.1'] },
    { bodyKey: 'home.norm.item.3.body', cites: ['1.5.4.4.2.1', '1.5.4.4.2.2'] },
    { bodyKey: 'home.norm.item.4.body', cites: ['1.5.7.1', '1.5.7.3.2º'] },
    { bodyKey: 'home.norm.item.5.body', cites: ['1.5.5.2'] },
    { bodyKey: 'home.norm.item.6.body', cites: ['1.5.3.3', '1.5.7.2.1'] },
  ];
  readonly deliverables = [1, 2, 3, 4, 5, 6] as const;

  readonly methodSteps: MethodStep[] = [
    {
      index: '01',
      image: 'assets/method/method-hse.svg',
      layout: 'text-first',
      titleKey: 'home.method.step1.title',
      bodyKey: 'home.method.step1.body',
    },
    {
      index: '02',
      image: 'assets/method/method-observe.svg',
      layout: 'image-first',
      titleKey: 'home.method.step2.title',
      bodyKey: 'home.method.step2.body',
    },
    {
      index: '03',
      image: 'assets/method/method-follow.svg',
      layout: 'text-first',
      titleKey: 'home.method.step3.title',
      bodyKey: 'home.method.step3.body',
    },
  ];

  dimensionKey(index: number, field: 'title' | 'body'): string {
    return `home.dim.${index}.${field}`;
  }

  statKey(index: number, field: 'value' | 'label' | 'body' | 'source'): string {
    return `home.stat.${index}.${field}`;
  }

  gainKey(index: number, field: 'title' | 'body'): string {
    return `home.gain.${index}.${field}`;
  }

  deliverKey(index: number): string {
    return `home.deliver.item.${index}`;
  }
}
