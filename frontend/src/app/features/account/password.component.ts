import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { ApiService } from '../../core/api.service';
import { I18nService, TranslatePipe } from '../../core/i18n';
import { isEmail } from '../billing/br-docs';

@Component({
  selector: 'app-password',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe, RouterLink],
  templateUrl: './password.component.html',
  styleUrls: ['./account.scss'],
})
export class PasswordComponent implements OnInit {
  mode: 'request' | 'sent' | 'choose' | 'done' | 'invalid' = 'request';
  email = '';
  password = '';
  passwordAgain = '';
  submitting = false;
  errorKey = '';
  fieldError = '';
  private token = '';

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    private i18n: I18nService,
  ) {}

  ngOnInit(): void {
    this.token = (this.route.snapshot.queryParamMap.get('t') || '').trim();
    if (this.token) this.mode = 'choose';
  }

  toggleLang(): void {
    this.i18n.setLang(this.i18n.lang() === 'pt-BR' ? 'en' : 'pt-BR');
  }

  request(): void {
    if (this.submitting) return;
    this.errorKey = '';
    const email = this.email.trim();
    if (!isEmail(email)) {
      this.fieldError = 'account.err.email';
      return;
    }
    this.fieldError = '';
    this.submitting = true;
    this.api.forgotPassword(email).subscribe({
      next: () => {
        this.submitting = false;
        this.mode = 'sent';
      },
      error: () => {
        this.submitting = false;
        this.errorKey = 'account.unreachable';
      },
    });
  }

  save(): void {
    if (this.submitting) return;
    this.errorKey = '';
    if (this.password.length < 8) {
      this.fieldError = 'account.err.password';
      return;
    }
    if (this.password !== this.passwordAgain) {
      this.fieldError = 'account.err.passwordMatch';
      return;
    }
    this.fieldError = '';
    this.submitting = true;
    this.api.resetPassword(this.token, this.password).subscribe({
      next: () => {
        this.password = '';
        this.passwordAgain = '';
        this.submitting = false;
        this.mode = 'done';
      },
      error: (err: HttpErrorResponse) => {
        this.submitting = false;
        if (err.status === 0 || err.status === 503) {
          this.errorKey = 'account.unreachable';
          return;
        }
        this.mode = 'invalid';
      },
    });
  }
}
