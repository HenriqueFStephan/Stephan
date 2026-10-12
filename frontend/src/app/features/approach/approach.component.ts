import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { TranslatePipe } from '../../core/i18n';
import { formatBrl } from '../billing/offer.config';
import { PlanId, plans, sizeBands } from '../billing/plans';

@Component({
  selector: 'app-approach',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslatePipe],
  templateUrl: './approach.component.html',
  styleUrls: ['./approach.component.scss'],
})
export class ApproachComponent {
  readonly plans = plans;
  readonly bands = sizeBands;

  starting(plan: PlanId): string {
    return formatBrl(sizeBands[0].monthlyCents[plan]);
  }

  fee(cents: number): string {
    return formatBrl(cents);
  }
}
