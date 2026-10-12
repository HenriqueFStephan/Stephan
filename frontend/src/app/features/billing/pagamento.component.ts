import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../core/api.service';
import { I18nService, MsgKey, TranslatePipe } from '../../core/i18n';
import {
  BillingDraft,
  BillingReceipt,
  DraftErrors,
  clearDraft,
  clearReceipt,
  loadDraft,
  loadReceipt,
  saveDraft,
  saveReceipt,
  toOrderPayload,
  validateCadastro,
  validatePayment,
} from './draft';
import { formatBrl, offer } from './offer.config';
import { bandForHeadcount, isPlanId, monthlyCents, planById } from './plans';
import { SupplierCardComponent } from './supplier-card.component';

@Component({
  selector: 'app-pagamento',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslatePipe, SupplierCardComponent],
  templateUrl: './pagamento.component.html',
  styleUrls: ['./billing.scss'],
})
export class PagamentoComponent implements OnInit {
  draft: BillingDraft | null = null;
  receipt: BillingReceipt | null = null;
  missingDraft = false;
  errors: DraftErrors = {};
  attempted = false;
  submitting = false;
  failed = false;
  readonly offer = offer;

  constructor(
    private api: ApiService,
    private i18n: I18nService,
  ) {}

  ngOnInit(): void {
    this.receipt = loadReceipt();
    if (this.receipt) return;
    const loaded = loadDraft();
    if (!loaded || Object.keys(validateCadastro(loaded)).length) {
      this.missingDraft = true;
      return;
    }
    this.draft = loaded;
  }

  toggleLang(): void {
    this.i18n.setLang(this.i18n.lang() === 'pt-BR' ? 'en' : 'pt-BR');
  }

  get includedKeys(): MsgKey[] {
    const plan = this.draft ? planById(this.draft.plan) : null;
    if (!plan) return [];
    return [...plan.featureKeys, ...plan.extraKeys];
  }

  get monthly(): number | null {
    if (!this.draft || !isPlanId(this.draft.plan)) return null;
    return monthlyCents(this.draft.plan, Number(this.draft.headcount));
  }

  get bandLabel(): string {
    if (!this.draft) return '';
    const band = bandForHeadcount(Number(this.draft.headcount));
    return band ? this.i18n.t(band.labelKey) : '';
  }

  planTitle(id: string | undefined): string {
    if (!id) return '';
    const plan = planById(id);
    return plan ? this.i18n.t(plan.titleKey) : '';
  }

  money(cents: number): string {
    return formatBrl(cents);
  }

  errorFor(key: keyof BillingDraft): string {
    return this.errors[key] ?? '';
  }

  get invalid(): boolean {
    return this.attempted && Object.keys(this.errors).length > 0;
  }

  get backLink(): string {
    const loaded = loadDraft();
    return loaded && isPlanId(loaded.plan) ? '/cadastro' : '/abordagem';
  }

  choose(method: string): void {
    if (!this.draft) return;
    if (method !== 'pix' && method !== 'boleto' && method !== 'card') return;
    this.draft.method = method;
    this.draft.installments = 1;
  }

  edit(): void {
    if (this.draft) saveDraft(this.draft);
  }

  submit(): void {
    if (!this.draft || this.submitting) return;
    const quoted = this.monthly;
    if (quoted == null) return;
    this.draft.installments = 1;
    this.attempted = true;
    this.failed = false;
    this.errors = validatePayment(this.draft, []);
    if (Object.keys(this.errors).length) return;
    saveDraft(this.draft);
    this.submitting = true;
    this.api.submitOrder(toOrderPayload(this.draft, quoted)).subscribe({
      next: (response) => {
        const receipt: BillingReceipt = {
          reference: response.reference,
          company: this.draft?.legalName.trim() || '',
          quotedCents: quoted,
          plan: this.draft?.plan ?? '',
        };
        clearDraft();
        saveReceipt(receipt);
        this.receipt = receipt;
        this.draft = null;
        this.submitting = false;
      },
      error: (_err: HttpErrorResponse) => {
        this.failed = true;
        this.submitting = false;
      },
    });
  }

  another(): void {
    clearReceipt();
    this.receipt = null;
  }
}
