import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { I18nService, TranslatePipe } from '../../core/i18n';
import { BRAZIL_STATES, maskCep, maskCnpj, maskCpf, maskPhone } from './br-docs';
import {
  BillingDraft,
  DraftErrors,
  applySameContact,
  clearReceipt,
  emptyDraft,
  loadDraft,
  saveDraft,
  validateCadastro,
} from './draft';
import { SupplierCardComponent } from './supplier-card.component';

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
  imports: [CommonModule, FormsModule, RouterLink, TranslatePipe, SupplierCardComponent],
  templateUrl: './cadastro.component.html',
  styleUrls: ['./billing.scss'],
})
export class CadastroComponent {
  readonly states = BRAZIL_STATES;
  draft: BillingDraft = loadDraft() ?? emptyDraft();
  errors: DraftErrors = {};
  attempted = false;
  cepState: 'idle' | 'loading' | 'miss' = 'idle';
  private cepTicket = 0;

  constructor(
    private router: Router,
    private i18n: I18nService,
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

  onCnpj(value: string): void {
    this.draft.cnpj = maskCnpj(value);
  }

  onCpf(value: string): void {
    this.draft.repCpf = maskCpf(value);
  }

  onPhone(field: 'phone' | 'repPhone' | 'contactPhone', value: string): void {
    this.draft[field] = maskPhone(value);
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
        this.draft.street = data.logradouro || this.draft.street;
        this.draft.district = data.bairro || this.draft.district;
        this.draft.city = data.localidade || this.draft.city;
        this.draft.state = data.uf || this.draft.state;
        this.cepState = 'idle';
      })
      .catch(() => {
        if (ticket === this.cepTicket) this.cepState = 'miss';
      });
  }

  continue(): void {
    this.attempted = true;
    applySameContact(this.draft);
    this.errors = validateCadastro(this.draft);
    if (Object.keys(this.errors).length) return;
    clearReceipt();
    saveDraft(this.draft);
    void this.router.navigate(['/pagamento']);
  }
}
