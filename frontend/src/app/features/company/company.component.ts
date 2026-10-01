import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/api.service';
import { I18nService, TranslatePipe } from '../../core/i18n';
import {
  CompanyAlphaRow,
  CompanyBandRow,
  CompanyOverview,
  CompanySectorRow,
  InvitationRoster,
  InvitationUploadResult,
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

interface WeekBar {
  x: number;
  y: number;
  width: number;
  height: number;
  count: number;
  label: string;
}

interface BandPart {
  key: Band;
  count: number;
  share: number;
}

@Component({
  selector: 'app-company',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './company.component.html',
  styleUrls: ['./company.component.scss'],
})
export class CompanyComponent implements OnInit {
  readonly bandKeys: Band[] = ['urgent', 'improve', 'good', 'maintain'];
  readonly chartWidth = 640;
  readonly chartHeight = 188;

  phase: 'login' | 'loading' | 'ready' = 'login';
  username = '';
  password = '';
  submitting = false;
  errorKey = '';
  overview: CompanyOverview | null = null;
  inviteFile: File | null = null;
  inviteSubmitting = false;
  inviteErrorKey = '';
  inviteUnknownColumns = '';
  inviteResult: InvitationUploadResult | null = null;
  roster: InvitationRoster | null = null;

  constructor(
    private api: ApiService,
    private i18n: I18nService,
  ) {}

  ngOnInit(): void {
    const stored = this.readPassage();
    if (stored) {
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
        sessionStorage.setItem(PASSAGE_KEY, response.passage);
        this.load(response.passage);
      },
      error: (err: HttpErrorResponse) => {
        this.submitting = false;
        this.errorKey = err.status === 0 ? 'company.unreachable' : 'company.badLogin';
      },
    });
  }

  logout(): void {
    sessionStorage.removeItem(PASSAGE_KEY);
    this.overview = null;
    this.password = '';
    this.errorKey = '';
    this.inviteFile = null;
    this.inviteResult = null;
    this.inviteErrorKey = '';
    this.inviteUnknownColumns = '';
    this.roster = null;
    this.phase = 'login';
  }

  onInviteFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.inviteFile = input.files && input.files.length ? input.files[0] : null;
    this.inviteResult = null;
    this.inviteErrorKey = '';
    this.inviteUnknownColumns = '';
  }

  uploadInvites(input: HTMLInputElement): void {
    const passage = this.readPassage();
    const file = this.inviteFile;
    if (!passage || !file || this.inviteSubmitting) {
      return;
    }
    this.inviteSubmitting = true;
    this.inviteErrorKey = '';
    this.inviteUnknownColumns = '';
    this.api.uploadCompanyInvitations(passage, file).subscribe({
      next: (result) => {
        this.inviteSubmitting = false;
        this.inviteResult = result;
        this.inviteFile = null;
        input.value = '';
        this.refreshRoster(passage);
      },
      error: (err: HttpErrorResponse) => {
        this.inviteSubmitting = false;
        this.inviteResult = null;
        const detail = err.error && err.error.detail;
        const code = detail && typeof detail === 'object' ? detail.code : '';
        if (code === 'unknown_columns') {
          this.inviteErrorKey = 'company.inviteUnknown';
          const columns = Array.isArray(detail.columns) ? detail.columns : [];
          this.inviteUnknownColumns = columns.join(', ');
        } else if (code === 'mail_not_configured') {
          this.inviteErrorKey = 'company.inviteMail';
        } else if (code === 'mail_failed') {
          this.inviteErrorKey = 'company.inviteMailFailed';
        } else if (code === 'database_unavailable' || err.status === 0 || err.status === 503) {
          this.inviteErrorKey = 'company.inviteUnreachable';
        } else {
          this.inviteErrorKey = 'company.inviteBadFile';
        }
      },
    });
  }

  companyLabel(): string {
    if (this.overview?.company_id === 'demo') {
      return this.i18n.t('company.demoName');
    }
    return this.overview?.company_id ?? '';
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

  formatIso(iso: string): string {
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

  weekBars(): WeekBar[] {
    const weeks = this.overview?.weeks ?? [];
    if (!weeks.length) {
      return [];
    }
    const max = Math.max(...weeks.map((week) => week.count), 1);
    const slot = this.chartWidth / weeks.length;
    const width = Math.min(36, slot * 0.55);
    return weeks.map((week, index) => {
      const height = week.count === 0 ? 0 : Math.max(4, (week.count / max) * 108);
      return {
        x: index * slot + (slot - width) / 2,
        y: 128 - height,
        width,
        height,
        count: week.count,
        label: this.formatIso(week.week).slice(0, 5),
      };
    });
  }

  weeksLabel(): string {
    return (this.overview?.weeks ?? [])
      .map((week) => `${this.formatIso(week.week)}: ${week.count}`)
      .join(', ');
  }

  overallAlpha(): CompanyAlphaRow | null {
    return this.overview?.alpha[0] ?? null;
  }

  private load(passage: string): void {
    this.phase = 'loading';
    this.api.getCompanyOverview(passage).subscribe({
      next: (overview) => {
        this.overview = overview;
        this.phase = 'ready';
        this.refreshRoster(passage);
      },
      error: (err: HttpErrorResponse) => {
        if (err.status === 401) {
          sessionStorage.removeItem(PASSAGE_KEY);
        }
        this.overview = null;
        this.phase = 'login';
        this.errorKey = err.status === 401 ? '' : 'company.unreachable';
      },
    });
  }

  private refreshRoster(passage: string): void {
    this.api.getCompanyInvitations(passage).subscribe({
      next: (roster) => {
        this.roster = roster;
        if (this.inviteErrorKey === 'company.inviteUnreachable') {
          this.inviteErrorKey = '';
        }
      },
      error: () => {
        this.roster = null;
        if (!this.inviteErrorKey) {
          this.inviteErrorKey = 'company.inviteUnreachable';
        }
      },
    });
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
