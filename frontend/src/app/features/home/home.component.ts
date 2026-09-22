import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';

import { ApiService } from '../../core/api.service';
import { I18nService, TranslatePipe } from '../../core/i18n';
import { ApiStatus } from '../../core/models';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, TranslatePipe],
  template: `
    <section class="home">
      <p class="kicker">{{ 'home.kicker' | t }}</p>
      <h1>{{ 'home.title' | t }}</h1>
      <p class="lead">{{ 'home.lead' | t }}</p>

      <article class="card" [class.card--ok]="status" [class.card--bad]="failed">
        <p class="card__state" *ngIf="loading">{{ 'home.checking' | t }}</p>
        <p class="card__state" *ngIf="status">{{ 'home.ok' | t }}</p>
        <p class="card__state" *ngIf="failed">{{ 'home.fail' | t }}</p>

        <dl *ngIf="status">
          <div>
            <dt>{{ 'home.environment' | t }}</dt>
            <dd>{{ status.environment }}</dd>
          </div>
          <div>
            <dt>{{ 'home.version' | t }}</dt>
            <dd>{{ status.version }}</dd>
          </div>
          <div>
            <dt>{{ 'home.studio' | t }}</dt>
            <dd>{{ status.studio_configured ? ('home.studioOn' | t) : ('home.studioOff' | t) }}</dd>
          </div>
          <div>
            <dt>{{ 'home.smtp' | t }}</dt>
            <dd>{{ status.smtp_configured ? ('home.smtpOn' | t) : ('home.smtpOff' | t) }}</dd>
          </div>
          <div>
            <dt>{{ 'home.endpoint' | t }}</dt>
            <dd><code>{{ endpoint }}</code></dd>
          </div>
        </dl>
      </article>
    </section>
  `,
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit {
  status: ApiStatus | null = null;
  loading = true;
  failed = false;
  readonly endpoint = `${environment.apiUrl}/status`;

  constructor(
    private api: ApiService,
    private i18n: I18nService,
  ) {}

  ngOnInit(): void {
    this.i18n.lang();
    this.api.getStatus().subscribe({
      next: (status) => {
        this.status = status;
        this.loading = false;
      },
      error: () => {
        this.failed = true;
        this.loading = false;
      },
    });
  }
}
