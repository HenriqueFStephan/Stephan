import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../core/api.service';
import { I18nService, TranslatePipe } from '../../core/i18n';
import {
  CompanyAlphaRow,
  CompanyBandRow,
  CompanyOverview,
  CompanyRoundRow,
  CompanySectorRow,
  InvitationUploadResult,
  ListQuote,
  ScheduledSend,
  SendFormsResult,
} from '../../core/models';
import {
  BAND_COPY,
  Band,
  DIMENSIONS,
  DIMENSION_ORDER,
  DimensionId,
  bandFor,
  barWidth,
  formatMean,
} from '../tool/hse-it';

const PASSAGE_KEY = 'stephan-company-passage';
const COMPANY_NAME_KEY = 'stephan-company-name';
const COMPANY_SLUG_KEY = 'stephan-company-slug';

interface DayBar {
  x: number;
  y: number;
  width: number;
  height: number;
  count: number;
  label: string;
  showCount: boolean;
}

interface BandPart {
  key: Band;
  count: number;
  share: number;
}

@Component({
  selector: 'app-company',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe, RouterLink],
  templateUrl: './company.component.html',
  styleUrls: ['./company.component.scss'],
})
export class CompanyComponent implements OnInit {
  readonly bandKeys: Band[] = ['urgent', 'improve', 'good', 'maintain'];
  readonly readings = [
    { id: 'dimensions', titleKey: 'company.dimensionsTitle', leadKey: 'company.dimensionsLead' },
    { id: 'bands', titleKey: 'company.bandsTitle', leadKey: 'company.bandsLead' },
    { id: 'sectors', titleKey: 'company.sectorsTitle', leadKey: 'company.sectorsLead' },
  ] as const;
  readonly chartWidth = 640;
  readonly chartHeight = 188;

  phase: 'login' | 'loading' | 'ready' = 'login';
  username = '';
  password = '';
  submitting = false;
  errorKey = '';
  overview: CompanyOverview | null = null;
  companyName = '';
  companySlug = '';
  inviteFile: File | null = null;
  inviteSubmitting = false;
  quoting = false;
  releaseSkip = false;
  inviteErrorKey = '';
  inviteUnknownColumns = '';
  inviteResult: InvitationUploadResult | null = null;
  preview: ListQuote | null = null;
  payMethod = '';
  payErrorKey = '';
  unsent: string[] = [];
  retrying = false;
  held = 0;
  scheduled: ScheduledSend[] = [];
  sendOpen = false;
  sendMode: 'now' | 'schedule' = 'now';
  sendTogether = true;
  videoAt = '';
  formAt = '';
  sending = false;
  sendErrorKey = '';
  sendResult: SendFormsResult | null = null;
  rounds: CompanyRoundRow[] | null = null;
  roundsError = false;
  selectedRound = '';
  statsRound = '';
  statsLoading = false;
  statsErrorKey = '';
  private statsRequest = 0;
  alphaOpen = false;
  reading: (typeof this.readings)[number]['id'] = 'dimensions';

  constructor(
    private api: ApiService,
    private i18n: I18nService,
  ) {}

  ngOnInit(): void {
    const stored = this.readPassage();
    if (stored) {
      this.companyName = sessionStorage.getItem(COMPANY_NAME_KEY) || '';
      this.companySlug = sessionStorage.getItem(COMPANY_SLUG_KEY) || '';
      this.load(stored);
    }
  }

  toggleLang(): void {
    this.i18n.setLang(this.i18n.lang() === 'pt-BR' ? 'en' : 'pt-BR');
  }

  login(): void {
    const username = this.username.trim();
    const password = this.password.trim();
    if (!username || !password || this.submitting) {
      return;
    }
    this.submitting = true;
    this.errorKey = '';
    this.api.loginCompany(username, password).subscribe({
      next: (response) => {
        this.password = '';
        this.submitting = false;
        this.companyName = response.company_name;
        this.companySlug = response.company_slug;
        sessionStorage.setItem(PASSAGE_KEY, response.passage);
        sessionStorage.setItem(COMPANY_NAME_KEY, response.company_name);
        sessionStorage.setItem(COMPANY_SLUG_KEY, response.company_slug);
        this.load(response.passage);
      },
      error: (err: HttpErrorResponse) => {
        const detail = err.error?.detail;
        const code = detail && typeof detail === 'object' ? String(detail.code ?? '') : '';
        this.submitting = false;
        this.errorKey = code === 'email_unconfirmed'
          ? 'company.unconfirmed'
          : err.status === 0 || err.status === 503
            ? 'company.unreachable'
            : 'company.badLogin';
      },
    });
  }

  logout(): void {
    sessionStorage.removeItem(PASSAGE_KEY);
    sessionStorage.removeItem(COMPANY_NAME_KEY);
    sessionStorage.removeItem(COMPANY_SLUG_KEY);
    this.companyName = '';
    this.companySlug = '';
    this.overview = null;
    this.password = '';
    this.errorKey = '';
    this.inviteFile = null;
    this.inviteResult = null;
    this.preview = null;
    this.payMethod = '';
    this.quoting = false;
    this.unsent = [];
    this.retrying = false;
    this.held = 0;
    this.scheduled = [];
    this.closeSend();
    this.sendResult = null;
    this.inviteErrorKey = '';
    this.inviteUnknownColumns = '';
    this.rounds = null;
    this.roundsError = false;
    this.selectedRound = '';
    this.statsRound = '';
    this.statsLoading = false;
    this.statsErrorKey = '';
    this.alphaOpen = false;
    this.phase = 'login';
  }

  canSkip(): boolean {
    return this.companySlug === 'internal';
  }

  onInviteFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.inviteFile = input.files && input.files.length ? input.files[0] : null;
    this.inviteResult = null;
    this.preview = null;
    this.payMethod = '';
    this.payErrorKey = '';
    this.inviteErrorKey = '';
    this.inviteUnknownColumns = '';
    if (this.inviteFile) {
      this.quoteInvites();
    }
  }

  quoteInvites(): void {
    const passage = this.readPassage();
    const file = this.inviteFile;
    if (!passage || !file) {
      return;
    }
    this.quoting = true;
    this.inviteErrorKey = '';
    this.inviteUnknownColumns = '';
    this.api.quoteCompanyInvitations(passage, file).subscribe({
      next: (preview) => {
        if (this.inviteFile !== file) {
          return;
        }
        this.quoting = false;
        this.preview = preview;
      },
      error: (err: HttpErrorResponse) => {
        if (this.inviteFile !== file) {
          return;
        }
        this.quoting = false;
        this.preview = null;
        this.applyInviteError(err);
      },
    });
  }

  releaseInvites(input: HTMLInputElement, skip: boolean): void {
    const passage = this.readPassage();
    const file = this.inviteFile;
    const forms = this.preview ? this.preview.forms : 0;
    if (!passage || !file || this.inviteSubmitting) {
      return;
    }
    if (skip && !this.canSkip()) {
      return;
    }
    if (!skip && forms > 0 && !this.payMethod) {
      return;
    }
    this.inviteSubmitting = true;
    this.releaseSkip = skip;
    this.inviteErrorKey = '';
    this.inviteUnknownColumns = '';
    this.payErrorKey = '';
    this.api.uploadCompanyInvitations(passage, file, skip ? '' : this.payMethod, skip).subscribe({
      next: (result) => {
        this.inviteSubmitting = false;
        this.inviteResult = result;
        this.preview = null;
        this.payMethod = '';
        this.inviteFile = null;
        input.value = '';
        this.refreshRounds(passage);
        this.refreshUnsent(passage);
      },
      error: (err: HttpErrorResponse) => {
        this.inviteSubmitting = false;
        this.applyInviteError(err);
      },
    });
  }

  money(cents: number): string {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(cents / 100);
  }

  private applyInviteError(err: HttpErrorResponse): void {
    const detail = err.error && err.error.detail;
    const code = detail && typeof detail === 'object' ? detail.code : '';
    if (code === 'unknown_columns') {
      this.inviteErrorKey = 'company.inviteUnknown';
      const columns = Array.isArray(detail.columns) ? detail.columns : [];
      this.inviteUnknownColumns = columns.join(', ');
    } else if (code === 'payment_required') {
      this.payErrorKey = 'company.payNeedMethod';
    } else if (code === 'mail_not_configured') {
      this.inviteErrorKey = 'company.inviteMail';
    } else if (code === 'whatsapp_not_configured') {
      this.inviteErrorKey = 'company.inviteWhatsapp';
    } else if (code === 'channels_not_configured') {
      this.inviteErrorKey = 'company.inviteChannels';
    } else if (code === 'mail_failed') {
      this.inviteErrorKey = 'company.inviteMailFailed';
    } else if (code === 'whatsapp_failed') {
      this.inviteErrorKey = 'company.inviteWhatsappFailed';
    } else if (code === 'database_unavailable' || err.status === 0 || err.status === 503) {
      this.inviteErrorKey = 'company.inviteUnreachable';
    } else {
      this.inviteErrorKey = 'company.inviteBadFile';
    }
  }

  openSend(): void {
    this.sendOpen = true;
    this.sendErrorKey = '';
    this.sendResult = null;
  }

  closeSend(): void {
    this.sendOpen = false;
    this.sendMode = 'now';
    this.sendTogether = true;
    this.videoAt = '';
    this.formAt = '';
    this.sending = false;
    this.sendErrorKey = '';
  }

  /** The earliest value a time field accepts: now, in the browser's own zone. */
  minLocal(): string {
    const now = new Date();
    const pad = (value: number) => String(value).padStart(2, '0');
    return (
      `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` +
      `T${pad(now.getHours())}:${pad(now.getMinutes())}`
    );
  }

  /** Why the chosen times cannot be sent, or an empty string when they can. */
  sendProblem(): string {
    if (this.sendMode === 'now') {
      return '';
    }
    const video = this.parseLocal(this.videoAt);
    if (video === null) {
      return 'company.sendNeedVideo';
    }
    // A minute of slack: the field has no seconds, so "now" is already a little in the past.
    if (video < Date.now() - 60_000) {
      return 'company.sendPast';
    }
    if (video > Date.now() + 365 * 24 * 3600 * 1000) {
      return 'company.sendTooFar';
    }
    if (this.sendTogether) {
      return '';
    }
    const form = this.parseLocal(this.formAt);
    if (form === null) {
      return 'company.sendNeedForm';
    }
    if (form < video) {
      return 'company.sendFormBefore';
    }
    if (form > Date.now() + 365 * 24 * 3600 * 1000) {
      return 'company.sendTooFar';
    }
    return '';
  }

  confirmSend(): void {
    const passage = this.readPassage();
    const problem = this.sendProblem();
    if (!passage || this.sending) {
      return;
    }
    if (problem) {
      this.sendErrorKey = problem;
      return;
    }
    this.sending = true;
    this.sendErrorKey = '';
    const request =
      this.sendMode === 'now'
        ? { mode: 'now' as const }
        : {
            mode: 'schedule' as const,
            video_at: new Date(this.videoAt).toISOString(),
            form_at: new Date(this.sendTogether ? this.videoAt : this.formAt).toISOString(),
          };
    this.api.sendCompanyInvitations(passage, request).subscribe({
      next: (result) => {
        this.sending = false;
        this.sendResult = result;
        this.sendOpen = false;
        this.videoAt = '';
        this.formAt = '';
        this.refreshUnsent(passage);
      },
      error: (err: HttpErrorResponse) => {
        this.sending = false;
        if (err.status === 401) {
          this.logout();
          return;
        }
        const detail = err.error && err.error.detail;
        const code = detail && typeof detail === 'object' ? String(detail.code ?? '') : '';
        this.sendErrorKey = this.sendErrorFor(code);
        if (code === 'nothing_to_send') {
          this.refreshUnsent(passage);
        }
      },
    });
  }

  /** A moment as day/month/year hour:minute, in the browser's own time zone. */
  stamp(iso: string | null): string {
    if (!iso) {
      return '-';
    }
    const when = new Date(iso);
    if (Number.isNaN(when.getTime())) {
      return '-';
    }
    const pad = (value: number) => String(value).padStart(2, '0');
    return (
      `${pad(when.getDate())}/${pad(when.getMonth() + 1)}/${when.getFullYear()} ` +
      `${pad(when.getHours())}:${pad(when.getMinutes())}`
    );
  }

  /** A scheduled send whose form time has passed is already on its way. */
  sendingNow(item: ScheduledSend): boolean {
    return new Date(item.form_at).getTime() <= Date.now();
  }

  private sendErrorFor(code: string): string {
    switch (code) {
      case 'form_before_video':
        return 'company.sendFormBefore';
      case 'too_far':
        return 'company.sendTooFar';
      case 'nothing_to_send':
        return 'company.sendNothing';
      case 'video_not_configured':
        return 'company.sendNoVideo';
      case 'mail_not_configured':
        return 'company.inviteMail';
      case 'whatsapp_not_configured':
        return 'company.inviteWhatsapp';
      case 'channels_not_configured':
        return 'company.inviteChannels';
      case 'database_unavailable':
        return 'company.inviteUnreachable';
      default:
        return 'company.sendFailed';
    }
  }

  private parseLocal(value: string): number | null {
    if (!value) {
      return null;
    }
    const time = new Date(value).getTime();
    return Number.isNaN(time) ? null : time;
  }

  retryUnsent(): void {
    const passage = this.readPassage();
    if (!passage || this.retrying || !this.unsent.length) {
      return;
    }
    this.retrying = true;
    this.inviteErrorKey = '';
    this.api.retryCompanyInvitations(passage).subscribe({
      next: () => {
        this.retrying = false;
        this.refreshUnsent(passage);
      },
      error: (err: HttpErrorResponse) => {
        this.retrying = false;
        const detail = err.error && err.error.detail;
        const code = detail && typeof detail === 'object' ? detail.code : '';
        if (code === 'mail_not_configured') {
          this.inviteErrorKey = 'company.inviteMail';
        } else if (code === 'whatsapp_not_configured') {
          this.inviteErrorKey = 'company.inviteWhatsapp';
        } else if (code === 'channels_not_configured') {
          this.inviteErrorKey = 'company.inviteChannels';
        } else {
          this.inviteErrorKey = 'company.inviteUnreachable';
        }
      },
    });
  }

  companyLabel(): string {
    if (this.companyName) {
      return this.companyName;
    }
    if (this.overview?.company_id === 'demo') {
      return this.i18n.t('company.demoName');
    }
    return this.overview?.company_id ?? '';
  }

  readingLead(): string {
    return this.readings.find((item) => item.id === this.reading)?.leadKey ?? 'company.dimensionsLead';
  }

  scaleName(id: string): string {
    if (id === 'overall') {
      return this.i18n.t('company.alphaOverall');
    }
    const dimension = this.asDimension(id);
    if (!dimension) {
      return id;
    }
    return this.i18n.lang() === 'en' ? DIMENSIONS[dimension].en : DIMENSIONS[dimension].pt;
  }

  dimensionAbout(id: string): string {
    const dimension = this.asDimension(id);
    if (!dimension) {
      return '';
    }
    return this.i18n.lang() === 'en' ? DIMENSIONS[dimension].aboutEn : DIMENSIONS[dimension].aboutPt;
  }

  sectorName(id: string): string {
    return this.i18n.t(`company.sector.${id}`);
  }

  meanText(value: number | null): string {
    if (value == null) {
      return '—';
    }
    return formatMean(value, this.i18n.lang());
  }

  alphaText(value: number | null): string {
    if (value == null) {
      return '—';
    }
    const text = value.toFixed(3);
    return this.i18n.lang() === 'pt-BR' ? text.replace('.', ',') : text;
  }

  formatIso(iso: string | null): string {
    if (!iso) {
      return '—';
    }
    const [year, month, day] = iso.split('-');
    if (!year || !month || !day) {
      return iso;
    }
    return this.i18n.lang() === 'en' ? `${month}/${day}/${year}` : `${day}/${month}/${year}`;
  }

  fill(mean: number): number {
    return barWidth(mean);
  }

  ticks(id: string): number[] {
    const dimension = this.asDimension(id);
    if (!dimension) {
      return [];
    }
    const copy = DIMENSIONS[dimension];
    return [copy.p20, copy.p50, copy.p80];
  }

  bandOf(id: string, mean: number): Band {
    const dimension = this.asDimension(id);
    return dimension ? bandFor(mean, dimension) : 'improve';
  }

  bandSentence(id: string, mean: number): string {
    return BAND_COPY[this.bandOf(id, mean)][this.i18n.lang()];
  }

  sectorMean(sector: CompanySectorRow, id: string): number {
    return sector.means.find((row) => row.id === id)?.mean ?? 0;
  }

  bandParts(row: CompanyBandRow): BandPart[] {
    const total = row.urgent + row.improve + row.good + row.maintain;
    return this.bandKeys
      .map((key) => ({
        key,
        count: row[key],
        share: total ? (row[key] / total) * 100 : 0,
      }))
      .filter((part) => part.count > 0);
  }

  dayBars(): DayBar[] {
    const days = this.overview?.days ?? [];
    if (!days.length) {
      return [];
    }
    const max = Math.max(...days.map((day) => day.count), 1);
    const inset = 24;
    const slot = (this.chartWidth - inset * 2) / days.length;
    const width = Math.min(28, slot * 0.72);
    const labelEvery = Math.max(1, Math.ceil((days.length * 56) / this.chartWidth));
    return days.map((day, index) => {
      const height = day.count === 0 ? 3 : Math.max(4, (day.count / max) * 108);
      const showLabel = index % labelEvery === 0 || index === days.length - 1;
      return {
        x: inset + index * slot + (slot - width) / 2,
        y: 128 - height,
        width,
        height,
        count: day.count,
        label: showLabel ? this.formatIso(day.day).slice(0, 5) : '',
        showCount: day.count > 0 && slot >= 16,
      };
    });
  }

  daysLabel(): string {
    return (this.overview?.days ?? [])
      .map((day) => `${this.formatIso(day.day)}: ${day.count}`)
      .join(', ');
  }

  overallAlpha(): CompanyAlphaRow | null {
    return this.overview?.alpha[0] ?? null;
  }

  hasMoreAlpha(): boolean {
    return (this.overview?.alpha.length ?? 0) > 1;
  }

  visibleAlpha(): CompanyAlphaRow[] {
    const rows = this.overview?.alpha ?? [];
    return this.alphaOpen ? rows : rows.slice(0, 1);
  }

  shareText(value: number | null): string {
    return value == null ? '—' : `${value}%`;
  }

  onRoundPicked(label: string): void {
    const showing = this.overview != null || this.statsLoading;
    if (!showing || label === this.statsRound) {
      return;
    }
    this.selectedRound = label;
    this.showRoundStats();
  }

  statsVisible(): boolean {
    return this.overview != null && this.statsRound === this.selectedRound;
  }

  roundOpenedOn(): string {
    const label = this.statsRound || this.selectedRound;
    return this.rounds?.find((round) => round.label === label)?.opened_on ?? '';
  }

  toggleRoundStats(): void {
    if (this.statsVisible() || this.statsLoading) {
      this.statsRequest += 1;
      this.statsLoading = false;
      this.overview = null;
      this.statsRound = '';
      this.statsErrorKey = '';
      this.alphaOpen = false;
      return;
    }
    this.showRoundStats();
  }

  showRoundStats(): void {
    const passage = this.readPassage();
    const label = this.selectedRound;
    if (!passage || !label) {
      return;
    }
    const request = (this.statsRequest += 1);
    this.statsLoading = true;
    this.statsErrorKey = '';
    this.api.getCompanyOverview(passage, label).subscribe({
      next: (overview) => {
        if (request !== this.statsRequest) {
          return;
        }
        this.statsLoading = false;
        this.overview = overview;
        this.statsRound = label;
        this.alphaOpen = false;
        this.reading = 'dimensions';
      },
      error: (err: HttpErrorResponse) => {
        if (request !== this.statsRequest) {
          return;
        }
        this.statsLoading = false;
        this.overview = null;
        this.statsRound = '';
        if (err.status === 401) {
          this.logout();
          return;
        }
        this.statsErrorKey = err.status === 404 ? 'company.statsMissing' : 'company.unreachable';
      },
    });
  }

  private load(passage: string): void {
    this.phase = 'loading';
    this.api.getCompanyRounds(passage).subscribe({
      next: (rounds) => {
        this.applyRounds(rounds);
        this.refreshUnsent(passage);
        this.phase = 'ready';
      },
      error: (err: HttpErrorResponse) => {
        if (err.status === 401) {
          sessionStorage.removeItem(PASSAGE_KEY);
          sessionStorage.removeItem(COMPANY_NAME_KEY);
          this.companyName = '';
          this.overview = null;
          this.phase = 'login';
          this.errorKey = '';
          return;
        }
        this.rounds = null;
        this.roundsError = true;
        this.phase = 'ready';
      },
    });
  }

  private refreshRounds(passage: string): void {
    this.api.getCompanyRounds(passage).subscribe({
      next: (rounds) => this.applyRounds(rounds),
      error: (err: HttpErrorResponse) => {
        if (err.status === 401) {
          this.logout();
          return;
        }
        this.rounds = null;
        this.roundsError = true;
      },
    });
  }

  private refreshUnsent(passage: string): void {
    this.api.getCompanyInvitations(passage).subscribe({
      next: (roster) => {
        this.unsent = roster.unsent || [];
        this.held = roster.held ?? 0;
        this.scheduled = roster.scheduled ?? [];
      },
      error: (err: HttpErrorResponse) => {
        if (err.status === 401) {
          this.logout();
        }
      },
    });
  }

  private applyRounds(rounds: CompanyRoundRow[]): void {
    this.rounds = rounds;
    this.roundsError = false;
    const stillThere = rounds.some((round) => round.label === this.selectedRound);
    if (!stillThere) {
      this.selectedRound = rounds[0]?.label ?? '';
      this.overview = null;
      this.statsRound = '';
      this.alphaOpen = false;
    }
  }

  private readPassage(): string {
    if (typeof sessionStorage === 'undefined') {
      return '';
    }
    return sessionStorage.getItem(PASSAGE_KEY) || '';
  }

  private asDimension(id: string): DimensionId | null {
    return (DIMENSION_ORDER as readonly string[]).includes(id) ? (id as DimensionId) : null;
  }
}
