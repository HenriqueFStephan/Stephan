import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/api.service';
import { TranslatePipe } from '../../core/i18n';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent {
  name = '';
  organization = '';
  email = '';
  message = '';
  sending = false;
  sent = false;
  failed = false;

  constructor(private api: ApiService) {}

  submit(): void {
    if (this.sending) {
      return;
    }
    this.sending = true;
    this.sent = false;
    this.failed = false;
    this.api
      .submitContact({
        name: this.name.trim(),
        organization: this.organization.trim(),
        email: this.email.trim(),
        message: this.message.trim(),
      })
      .subscribe({
        next: () => {
          this.sending = false;
          this.sent = true;
          this.name = '';
          this.organization = '';
          this.email = '';
          this.message = '';
        },
        error: () => {
          this.sending = false;
          this.failed = true;
        },
      });
  }
}
