import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { ApiService } from '../../core/api.service';
import { I18nService, TranslatePipe } from '../../core/i18n';
import { isEmail } from '../billing/br-docs';

@Component({
  selector: 'app-confirm',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe, RouterLink],
  templateUrl: './confirm.component.html',
  styleUrls: ['./account.scss'],
})
export class ConfirmComponent implements OnInit {
  phase: 'working' | 'done' | 'invalid' | 'missing' | 'error' = 'working';
  email = '';
  submitting = false;
  sent = false;
  errorKey = '';
  emailError = '';

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    private i18n: I18nService,
  ) {}

  ngOnInit(): void {
    const token = (this.route.snapshot.queryParamMap.get('t') || '').trim();
    if (!token) {
      this.phase = 'missing';
      return;
    }
    this.api.confirmAccount(token).subscribe({
      next: () => {
        this.phase = 'done';
      },
      error: (err: HttpErrorResponse) => {
        if (err.status === 0 || err.status === 503) {
          this.phase = 'error';
          this.errorKey = 'account.unreachable';
          return;
        }
        this.phase = 'invalid';
      },
    });
  }

  toggleLang(): void {
    this.i18n.setLang(this.i18n.lang() === 'pt-BR' ? 'en' : 'pt-BR');
  }

  resend(): void {
    if (this.submitting) return;
    this.sent = false;
    this.errorKey = '';
    const email = this.email.trim();
    if (!isEmail(email)) {
      this.emailError = 'account.err.email';
      return;
    }
    this.emailError = '';
    this.submitting = true;
    this.api.resendConfirmation(email).subscribe({
      next: () => {
        this.submitting = false;
        this.sent = true;
      },
      error: () => {
        this.submitting = false;
        this.errorKey = 'account.unreachable';
      },
    });
  }
}
