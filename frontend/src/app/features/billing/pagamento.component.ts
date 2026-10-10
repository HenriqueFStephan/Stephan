import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../core/api.service';
import { I18nService, TranslatePipe } from '../../core/i18n';
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
import {
  CardPlan,
  cardPlans,
  formatBrl,
  formatRate,
  issAmountCents,
  offer,
  totalCents,
} from './offer.config';
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

  get plans(): CardPlan[] {
    return cardPlans();
  }

  get total(): number | null {
    return totalCents();
  }

  get iss(): number | null {
    return issAmountCents();
  }

  get breakdown(): { service: number; iss: number; total: number; rate: string; issIncluded: boolean } | null {
    const total = this.total;
    const iss = this.iss;
    const service = offer.price.cents;
    if (total == null || iss == null || service == null) return null;
    return {
      service,
      iss,
      total,
      rate: this.rate(),
      issIncluded: offer.price.issIncluded,
    };
  }

  money(cents: number): string {
    return formatBrl(cents);
  }

  rate(): string {
    const value = offer.price.issRatePercent;
    return value == null ? '' : formatRate(value);
  }

  errorFor(key: keyof BillingDraft): string {
    return this.errors[key] ?? '';
  }

  get invalid(): boolean {
    return this.attempted && Object.keys(this.errors).length > 0;
  }

  slice(plan: CardPlan): string {
    return formatBrl(plan.totalCents / plan.count);
  }

  choose(method: string): void {
    if (!this.draft) return;
    if (method !== 'pix' && method !== 'boleto' && method !== 'card') return;
    this.draft.method = method;
    if (method !== 'card') this.draft.installments = 1;
    else if (!this.plans.some((plan) => plan.count === this.draft?.installments)) {
      this.draft.installments = 1;
    }
  }

  planLabel(plan: CardPlan): string {
    const total = formatBrl(plan.totalCents);
    if (plan.count === 1) return this.i18n.t('bill.planCash', { amount: total });
    if (plan.evenSlice && plan.totalCents === this.total) {
      return this.i18n.t('bill.planEven', { count: plan.count, slice: this.slice(plan), total });
    }
    return this.i18n.t('bill.planInterest', { count: plan.count, total });
  }

  edit(): void {
    if (this.draft) saveDraft(this.draft);
  }

  submit(): void {
    if (!this.draft || this.submitting) return;
    this.attempted = true;
    this.failed = false;
    this.errors = validatePayment(
      this.draft,
      this.plans.map((plan) => plan.count),
    );
    if (Object.keys(this.errors).length) return;
    saveDraft(this.draft);
    this.submitting = true;
    const quoted = this.total;
    this.api.submitOrder(toOrderPayload(this.draft, quoted)).subscribe({
      next: (response) => {
        const receipt: BillingReceipt = {
          reference: response.reference,
          company: this.draft?.legalName.trim() || '',
          quotedCents: quoted,
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
