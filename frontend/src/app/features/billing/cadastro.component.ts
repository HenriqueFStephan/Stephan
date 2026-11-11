import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/api.service';
import { I18nService, MsgKey, TranslatePipe } from '../../core/i18n';
import { CnpjCard } from '../../core/models';
import { BRAZIL_STATES, isCnpj, maskCep, maskCnpj, maskPhone, onlyDigits } from './br-docs';
import {
  BillingDraft,
  BillingReceipt,
  DraftErrors,
  clearDraft,
  emptyDraft,
  loadDraft,
  saveDraft,
  toOrderPayload,
  validateCadastro,
} from './draft';
import { offer } from './offer.config';

interface ViaCep {
  erro?: boolean;
  logradouro?: string;
  bairro?: string;
  localidade?: string;
  uf?: string;
}

@Component({
  selector: 'app-cadastro',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './cadastro.component.html',
  styleUrls: ['./billing.scss'],
})
export class CadastroComponent implements OnDestroy {
  readonly states = BRAZIL_STATES;
  readonly offer = offer;
  draft: BillingDraft = loadDraft() ?? emptyDraft();
  receipt: BillingReceipt | null = null;
  errors: DraftErrors = {};
  attempted = false;
  submitting = false;
  failed = false;
  failKey: MsgKey = 'bill.fail';
  cepState: 'idle' | 'loading' | 'miss' = 'idle';
  cnpjState: 'idle' | 'loading' | 'filled' | 'inactive' | 'miss' = 'idle';
  private cepTicket = 0;
  private cnpjTicket = 0;
  private cnpjApplied = '';
  private cnpjPending = '';
  private gone = false;

  constructor(
    private i18n: I18nService,
    private api: ApiService,
  ) {}

  toggleLang(): void {
    this.i18n.setLang(this.i18n.lang() === 'pt-BR' ? 'en' : 'pt-BR');
  }

  errorFor(key: keyof BillingDraft): string {
    return this.errors[key] ?? '';
  }

  get invalid(): boolean {
    return this.attempted && Object.keys(this.errors).length > 0;
  }

  ngOnDestroy(): void {
    this.gone = true;
    this.cnpjTicket += 1;
  }

  onCnpj(value: string): void {
    this.draft.cnpj = maskCnpj(value);
    const digits = onlyDigits(this.draft.cnpj);
    if (digits.length === 14 && isCnpj(digits)) {
      this.lookupCnpj();
      return;
    }
    this.cnpjTicket += 1;
    this.cnpjPending = '';
    this.cnpjState = 'idle';
  }

  lookupCnpj(): void {
    const digits = onlyDigits(this.draft.cnpj);
    if (!isCnpj(digits)) return;
    if (digits === this.cnpjApplied || digits === this.cnpjPending) return;
    const ticket = ++this.cnpjTicket;
    this.cnpjPending = digits;
    this.cnpjState = 'loading';
    this.api.lookupCnpj(digits).subscribe({
      next: (card) => {
        if (this.gone || ticket !== this.cnpjTicket) return;
        this.cnpjPending = '';
        this.applyCard(card);
        this.cnpjApplied = digits;
        this.cnpjState = card.active ? 'filled' : 'inactive';
      },
      error: () => {
        if (this.gone || ticket !== this.cnpjTicket) return;
        this.cnpjPending = '';
        this.cnpjState = 'miss';
      },
    });
  }

  private applyCard(card: CnpjCard): void {
    const put = (value: string, assign: (next: string) => void) => {
      const next = value.trim();
      if (next) assign(next);
    };
    put(card.legal_name, (next) => (this.draft.legalName = next));
    this.draft.tradeName = card.trade_name.trim();
    put(card.cnae, (next) => (this.draft.cnae = next));
    put(card.activity, (next) => (this.draft.activity = next));
    const phone = onlyDigits(card.phone);
    if (phone.length === 10 || phone.length === 11) this.draft.phone = maskPhone(phone);
    const cep = onlyDigits(card.postal_code);
    if (cep.length === 8) this.draft.postalCode = maskCep(cep);
    put(card.street, (next) => (this.draft.street = next));
    put(card.number, (next) => (this.draft.number = next));
    this.draft.complement = card.complement.trim();
    put(card.district, (next) => (this.draft.district = next));
    put(card.city, (next) => (this.draft.city = next));
    if ((BRAZIL_STATES as readonly string[]).includes(card.state)) this.draft.state = card.state;
    if (cep.length === 8) this.lookupCep();
  }

  onPhone(value: string): void {
    this.draft.phone = maskPhone(value);
  }

  onCep(value: string): void {
    this.draft.postalCode = maskCep(value);
    if (this.draft.postalCode.replace(/\D/g, '').length === 8) this.lookupCep();
  }

  lookupCep(): void {
    const cep = this.draft.postalCode.replace(/\D/g, '');
    if (cep.length !== 8) return;
    const ticket = ++this.cepTicket;
    this.cepState = 'loading';
    fetch(`https://viacep.com.br/ws/${cep}/json/`)
      .then((response) => response.json() as Promise<ViaCep>)
      .then((data) => {
        if (ticket !== this.cepTicket) return;
        if (!data || data.erro) {
          this.cepState = 'miss';
          return;
        }
        if (data.logradouro) this.draft.street = data.logradouro;
        this.draft.district = data.bairro || this.draft.district;
        this.draft.city = data.localidade || this.draft.city;
        this.draft.state = data.uf || this.draft.state;
        this.cepState = 'idle';
      })
      .catch(() => {
        if (ticket === this.cepTicket) this.cepState = 'miss';
      });
  }

  register(): void {
    if (this.submitting) return;
    this.attempted = true;
    this.failed = false;
    this.failKey = 'bill.fail';
    this.errors = validateCadastro(this.draft);
    if (Object.keys(this.errors).length) return;
    saveDraft(this.draft);
    this.submitting = true;
    this.api.submitOrder(toOrderPayload(this.draft)).subscribe({
      next: (response) => {
        this.receipt = {
          reference: response.reference,
          company: this.draft.legalName.trim(),
          email: this.draft.accessEmail.trim(),
          quotedCents: null,
          plan: '',
        };
        clearDraft();
        this.submitting = false;
      },
      error: (err: HttpErrorResponse) => {
        const detail = err.error?.detail;
        const code = detail && typeof detail === 'object' ? String(detail.code ?? '') : '';
        this.failKey = code === 'email_taken'
          ? 'bill.err.emailTaken'
          : code === 'cnpj_taken'
            ? 'bill.err.cnpjTaken'
            : code === 'mail_not_configured' || code === 'mail_failed'
              ? 'bill.mailFail'
              : 'bill.fail';
        this.failed = true;
        this.submitting = false;
      },
    });
  }
}
