import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/api.service';
import { I18nService, TranslatePipe } from '../../core/i18n';
import {
  BAND_COPY,
  DIMENSIONS,
  DIMENSION_ORDER,
  DimensionId,
  DimensionScore,
  HSE_ITEMS,
  HseItem,
  SCALE_LABELS,
  barWidth,
  formatMean,
  hseSummary,
  scoreHse,
} from './hse-it';

type Phase = 'checking' | 'invalid' | 'used' | 'intro' | 'ask' | 'results';

const ADVANCE_MS = 180;

@Component({
  selector: 'app-tool',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './tool.component.html',
  styleUrls: ['./tool.component.scss'],
})
export class ToolComponent implements OnInit, OnDestroy {
  readonly dimensions = DIMENSION_ORDER;
  readonly items = HSE_ITEMS;

  phase: Phase = 'intro';
  index = 0;
  sector = '';
  answers: (number | null)[] = Array(HSE_ITEMS.length).fill(null);
  scores: DimensionScore[] = [];
  copied = false;
  summaryText = '';
  campaign = false;
  saving = false;
  saveFailed = false;

  private token = '';
  private advanceTimer: number | null = null;

  constructor(
    readonly i18n: I18nService,
    private api: ApiService,
  ) {}

  ngOnInit(): void {
    const token = this.readToken();
    if (!token) {
      return;
    }
    this.campaign = true;
    this.token = token;
    this.phase = 'checking';
    this.api.openTool(token).subscribe({
      next: () => {
        this.phase = 'intro';
      },
      error: (err: HttpErrorResponse) => {
        const code = err.error && err.error.detail && err.error.detail.code;
        this.phase = err.status === 409 || code === 'link_used' ? 'used' : 'invalid';
      },
    });
  }

  ngOnDestroy(): void {
    this.clearAdvance();
  }

  get current(): HseItem {
    return this.items[this.index];
  }

  toggleLang(): void {
    this.i18n.setLang(this.i18n.lang() === 'pt-BR' ? 'en' : 'pt-BR');
  }

  start(): void {
    this.phase = 'ask';
    this.index = 0;
    this.reveal();
  }

  choose(value: number): void {
    this.answers[this.index] = value;
    this.copied = false;
    if (this.index >= this.items.length - 1) {
      this.clearAdvance();
      return;
    }
    this.clearAdvance();
    this.advanceTimer = window.setTimeout(() => {
      this.advanceTimer = null;
      if (this.index < this.items.length - 1) {
        this.index += 1;
        this.reveal();
      }
    }, ADVANCE_MS);
  }

  back(): void {
    this.clearAdvance();
    if (this.phase === 'results') {
      this.phase = 'ask';
      this.index = this.items.length - 1;
      this.reveal();
      return;
    }
    if (this.index > 0) {
      this.index -= 1;
      this.reveal();
    }
  }

  finish(): void {
    if (this.answers.some((value) => value == null) || this.saving) {
      return;
    }
    this.clearAdvance();
    if (!this.campaign) {
      this.showResults();
      return;
    }
    this.saving = true;
    this.saveFailed = false;
    const area = this.sector.trim();
    this.api
      .submitTool(this.token, this.answers as number[], area ? { area } : {})
      .subscribe({
        next: () => {
          this.saving = false;
          this.showResults();
        },
        error: () => {
          this.saving = false;
          this.saveFailed = true;
        },
      });
  }

  restart(): void {
    this.clearAdvance();
    this.answers = Array(this.items.length).fill(null);
    this.scores = [];
    this.index = 0;
    this.phase = 'intro';
    this.copied = false;
    this.summaryText = '';
    this.reveal();
  }

  async copySummary(): Promise<void> {
    const text = hseSummary(this.scores, this.sector, this.i18n.lang());
    this.summaryText = '';
    try {
      await navigator.clipboard.writeText(text);
      this.copied = true;
    } catch {
      this.copied = false;
      this.summaryText = text;
    }
  }

  itemText(item: HseItem): string {
    return this.i18n.lang() === 'en' ? item.en : item.pt;
  }

  scaleLabels(item: HseItem): readonly string[] {
    return SCALE_LABELS[item.scale][this.i18n.lang()];
  }

  dimensionName(id: DimensionId): string {
    const copy = DIMENSIONS[id];
    return this.i18n.lang() === 'en' ? copy.en : copy.pt;
  }

  dimensionAbout(id: DimensionId): string {
    const copy = DIMENSIONS[id];
    return this.i18n.lang() === 'en' ? copy.aboutEn : copy.aboutPt;
  }

  bandText(band: DimensionScore['band']): string {
    return BAND_COPY[band][this.i18n.lang()];
  }

  meanText(mean: number): string {
    return formatMean(mean, this.i18n.lang());
  }

  fillWidth(mean: number): number {
    return barWidth(mean);
  }

  ticks(id: DimensionId): number[] {
    const copy = DIMENSIONS[id];
    return [copy.p20, copy.p50, copy.p80];
  }

  @HostListener('window:keydown', ['$event'])
  onKey(event: KeyboardEvent): void {
    if (this.phase !== 'ask') {
      return;
    }
    const target = event.target as HTMLElement | null;
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
      return;
    }
    if (event.key >= '1' && event.key <= '5') {
      event.preventDefault();
      this.choose(Number(event.key));
      return;
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      this.back();
      return;
    }
    if (
      event.key === 'ArrowRight' &&
      this.answers[this.index] != null &&
      this.index < this.items.length - 1
    ) {
      event.preventDefault();
      this.clearAdvance();
      this.index += 1;
      this.reveal();
    }
  }

  private showResults(): void {
    this.scores = scoreHse(this.answers as number[]);
    this.phase = 'results';
    this.copied = false;
    this.summaryText = '';
    this.reveal();
  }

  private readToken(): string {
    if (typeof window === 'undefined') {
      return '';
    }
    return new URLSearchParams(window.location.search).get('t')?.trim() || '';
  }

  private reveal(): void {
    if (typeof window === 'undefined') {
      return;
    }
    window.scrollTo(0, 0);
  }

  private clearAdvance(): void {
    if (this.advanceTimer != null) {
      window.clearTimeout(this.advanceTimer);
      this.advanceTimer = null;
    }
  }
}
