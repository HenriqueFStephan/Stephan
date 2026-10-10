import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

import { TranslatePipe } from '../../core/i18n';
import { offer, offerGaps, supplierAddress } from './offer.config';

@Component({
  selector: 'app-supplier-card',
  standalone: true,
  imports: [CommonModule, TranslatePipe],
  template: `
    <section class="card supplier">
      <h2>{{ 'bill.supplierTitle' | t }}</h2>
      <p *ngIf="offer.supplier.legalName"><strong>{{ offer.supplier.legalName }}</strong></p>
      <p *ngIf="offer.supplier.cnpj">CNPJ {{ offer.supplier.cnpj }}</p>
      <p *ngIf="offer.supplier.municipalRegistration">
        {{ 'bill.municipal' | t }} {{ offer.supplier.municipalRegistration }}
      </p>
      <p *ngIf="address">{{ address }}</p>
      <p *ngIf="offer.supplier.email">{{ offer.supplier.email }}</p>
      <p *ngIf="offer.supplier.phone">{{ offer.supplier.phone }}</p>
      <p *ngIf="offer.supplier.sacEmail">{{ 'bill.sac' | t:{ email: offer.supplier.sacEmail } }}</p>
      <p *ngIf="offer.supplier.privacyEmail">
        {{ 'bill.privacyContact' | t:{ email: offer.supplier.privacyEmail } }}
      </p>
      <p *ngIf="offer.supplier.councilRegistration">{{ offer.supplier.councilRegistration }}</p>
      <p class="note" *ngIf="gaps.length">{{ 'bill.supplierGap' | t }}</p>
      <ul class="gap" *ngIf="gaps.length">
        <li *ngFor="let gap of gaps">{{ ('bill.gap.' + gap) | t }}</li>
      </ul>
      <p class="note" *ngIf="!gaps.length">{{ 'bill.supplierReady' | t }}</p>
    </section>
  `,
  styleUrls: ['./billing.scss'],
})
export class SupplierCardComponent {
  readonly offer = offer;
  readonly gaps = offerGaps();
  readonly address = supplierAddress();
}
