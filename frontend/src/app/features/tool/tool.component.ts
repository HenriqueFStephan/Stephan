import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { ApiService } from '../../core/api.service';
import { I18nService, TranslatePipe } from '../../core/i18n';
import { ToolDraft } from '../../core/models';
import {
  Band,
  DIMENSIONS,
  DimensionId,
  DimensionScore,
  HSE_ITEMS,
  HseItem,
  SCALE_LABELS,
  formatMean,
  hseSummary,
  scoreHse,
} from './hse-it';
import {
  PROFILE_QUESTIONS,
  ProfileOption,
  ProfileQuestion,
  isProfileReady,
  profilePayload,
} from './profile';

type Phase = 'checking' | 'invalid' | 'used' | 'intro' | 'profile' | 'ask' | 'results';

const ADVANCE_MS = 180;

@Component({
  selector: 'app-tool',
  standalone: true,
  imports: [CommonModule, TranslatePipe],
  templateUrl: './tool.component.html',
  styleUrls: ['./tool.component.scss'],
})
export class ToolComponent implements OnInit, OnDestroy {
  readonly items = HSE_ITEMS;
  readonly profileQuestions = PROFILE_QUESTIONS;

  phase: Phase = 'intro';
  index = 0;
  sector = '';
  profile: Record<string, string> = {};
  answers: (number | null)[] = Array(HSE_ITEMS.length).fill(null);
  scores: DimensionScore[] = [];
  copied = false;
  summaryText = '';
  campaign = false;
  saving = false;
  saveFailed = false;
  drafting = false;
  draftSaved = false;
  draftFailed = false;
  resumed = false;

  private token = '';
  private advanceTimer: number | null = null;
  private draftTimer: number | null = null;
  private draftDirty = false;

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
      next: (body) => {
        if (body.draft) {
          this.applyDraft(body.draft);
        } else {
          this.phase = 'intro';
        }
      },
      error: (err: HttpErrorResponse) => {
        const code = err.error && err.error.detail && err.error.detail.code;
        this.phase = err.status === 409 || code === 'link_used' ? 'used' : 'invalid';
      },
    });
  }

  ngOnDestroy(): void {
    this.clearAdvance();
    this.clearDraftTimer();
  }

  get current(): HseItem {
    return this.items[this.index];
  }

  get profileReady(): boolean {
    return isProfileReady(this.profile);
  }

  toggleLang(): void {
    this.i18n.setLang(this.i18n.lang() === 'pt-BR' ? 'en' : 'pt-BR');
  }

  start(): void {
    this.phase = 'profile';
    this.reveal();
  }

  questionText(question: ProfileQuestion): string {
    return this.i18n.lang() === 'en' ? question.en : question.pt;
  }

  optionText(option: ProfileOption): string {
    return this.i18n.lang() === 'en' ? option.en : option.pt;
  }

  chooseProfile(questionId: string, optionId: string): void {
    this.profile = { ...this.profile, [questionId]: optionId };
    this.noteDraftChanged();
  }

  continueProfile(): void {
    if (!this.profileReady) {
      return;
    }
    this.noteDraftChanged();
    this.phase = 'ask';
    this.reveal();
  }

  choose(value: number): void {
    this.answers[this.index] = value;
    this.copied = false;
    this.noteDraftChanged();
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

  saveDraft(): void {
    this.clearDraftTimer();
    if (!this.campaign || this.drafting || this.saving) {
      return;
    }
    if (this.phase !== 'profile' && this.phase !== 'ask') {
      return;
    }
    this.clearAdvance();
    this.drafting = true;
    this.draftSaved = false;
    this.draftFailed = false;
    const place = this.phase;
    this.api
      .saveToolDraft(this.token, {
        place,
        index: place === 'ask' ? this.index : 0,
        demographics: profilePayload(this.profile),
        answers: this.answers,
      })
      .subscribe({
        next: () => {
          this.drafting = false;
          this.draftSaved = true;
          this.draftDirty = false;
          this.resumed = false;
        },
        error: (err: HttpErrorResponse) => {
          this.drafting = false;
          if (this.linkWasUsed(err)) {
            this.phase = 'used';
            return;
          }
          this.draftFailed = true;
        },
      });
  }

  back(): void {
    this.clearAdvance();
    this.noteDraftChanged();
    if (this.phase === 'ask') {
      if (this.index > 0) {
        this.index -= 1;
      } else {
        this.phase = 'profile';
      }
      this.reveal();
      return;
    }
    if (this.phase === 'profile') {
      this.phase = 'intro';
      this.reveal();
    }
  }

  finish(): void {
    if (this.answers.some((value) => value == null) || this.saving || !this.profileReady) {
      return;
    }
    this.clearAdvance();
    this.clearDraftTimer();
    if (!this.campaign) {
      this.showResults();
      return;
    }
    this.saving = true;
    this.saveFailed = false;
    this.api
      .submitTool(this.token, this.answers as number[], profilePayload(this.profile))
      .subscribe({
        next: () => {
          this.saving = false;
          this.draftDirty = false;
          this.showResults();
        },
        error: (err: HttpErrorResponse) => {
          this.saving = false;
          if (this.linkWasUsed(err)) {
            this.draftDirty = false;
            this.showResults();
            return;
          }
          if (err.status === 0 || err.status >= 500) {
            this.confirmStored();
            return;
          }
          this.saveFailed = true;
        },
      });
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

  meanText(mean: number): string {
    return formatMean(mean, this.i18n.lang());
  }

  stripeName(band: Band): string {
    const names: Record<Band, Record<'pt-BR' | 'en', string>> = {
      urgent: { 'pt-BR': 'Preto', en: 'Black' },
      improve: { 'pt-BR': 'Vermelho', en: 'Red' },
      good: { 'pt-BR': 'Amarelo', en: 'Yellow' },
      maintain: { 'pt-BR': 'Verde', en: 'Green' },
    };
    return names[band][this.i18n.lang()];
  }

  @HostListener('window:beforeunload', ['$event'])
  onLeave(event: BeforeUnloadEvent): void {
    if (!this.campaign || (!this.draftDirty && !this.drafting)) {
      return;
    }
    event.preventDefault();
    event.returnValue = '';
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

  private applyDraft(draft: ToolDraft): void {
    const profile: Record<string, string> = {};
    const saved = draft.demographics || {};
    for (const question of PROFILE_QUESTIONS) {
      const value = saved[question.id];
      if (typeof value === 'string' && question.options.some((option) => option.id === value)) {
        profile[question.id] = value;
      }
    }
    this.profile = profile;
    const marks = Array.isArray(draft.answers) ? draft.answers : [];
    this.answers = Array.from({ length: this.items.length }, (_, position) => {
      const value = marks[position];
      return typeof value === 'number' && value >= 1 && value <= 5 ? value : null;
    });
    if (draft.place === 'ask' && this.profileReady) {
      const index = Number(draft.index);
      this.index = Number.isInteger(index) ? Math.min(this.items.length - 1, Math.max(0, index)) : 0;
      this.phase = 'ask';
    } else {
      this.index = 0;
      this.phase = 'profile';
    }
    this.resumed = true;
    this.reveal();
  }

  private noteDraftChanged(): void {
    this.draftSaved = false;
    this.draftFailed = false;
    this.resumed = false;
    this.draftDirty = true;
    this.scheduleDraft();
  }

  private scheduleDraft(): void {
    if (!this.campaign || this.saving) {
      return;
    }
    this.clearDraftTimer();
    this.draftTimer = window.setTimeout(() => {
      this.draftTimer = null;
      this.saveDraft();
    }, 1000);
  }

  private confirmStored(): void {
    this.api.openTool(this.token).subscribe({
      next: () => {
        this.saveFailed = true;
      },
      error: (err: HttpErrorResponse) => {
        if (this.linkWasUsed(err)) {
          this.draftDirty = false;
          this.showResults();
          return;
        }
        this.saveFailed = true;
      },
    });
  }

  private linkWasUsed(err: HttpErrorResponse): boolean {
    const code = err.error && err.error.detail && err.error.detail.code;
    return err.status === 409 || code === 'link_used';
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

  private clearDraftTimer(): void {
    if (this.draftTimer != null) {
      window.clearTimeout(this.draftTimer);
      this.draftTimer = null;
    }
  }
}
