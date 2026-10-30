import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { TranslatePipe } from '../../core/i18n';

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
  readonly normItems = [1, 2, 3, 4, 5, 6] as const;
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

  normKey(index: number): string {
    return `home.norm.item.${index}`;
  }

  deliverKey(index: number): string {
    return `home.deliver.item.${index}`;
  }
}
