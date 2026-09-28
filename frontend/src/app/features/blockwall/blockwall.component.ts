import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/api.service';
import { I18nService, TranslatePipe } from '../../core/i18n';

const PASSAGE_KEY = 'stephan-blockwall';

@Component({
  selector: 'app-blockwall',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './blockwall.component.html',
  styleUrls: ['./blockwall.component.scss'],
})
export class BlockwallComponent implements OnInit {
  @Output() cleared = new EventEmitter<void>();

  phase: 'pending' | 'locked' = 'pending';
  password = '';
  submitting = false;
  errorKey = '';

  constructor(
    private api: ApiService,
    private i18n: I18nService,
  ) {}

  ngOnInit(): void {
    this.api.getBlockwall().subscribe({
      next: (status) => {
        if (!status.enabled) {
          this.cleared.emit();
          return;
        }
        const stored = this.readPassage();
        if (!stored) {
          this.phase = 'locked';
          return;
        }
        this.api.resumeBlockwall(stored).subscribe({
          next: () => this.cleared.emit(),
          error: () => {
            this.clearPassage();
            this.phase = 'locked';
          },
        });
      },
      error: () => {
        this.phase = 'locked';
        this.errorKey = 'wall.unreachable';
      },
    });
  }

  toggleLang(): void {
    this.i18n.setLang(this.i18n.lang() === 'pt-BR' ? 'en' : 'pt-BR');
  }

  unlock(): void {
    const password = this.password.trim();
    if (!password || this.submitting) {
      return;
    }
    this.submitting = true;
    this.errorKey = '';
    this.api.unlockBlockwall(password).subscribe({
      next: (response) => {
        this.password = '';
        this.submitting = false;
        if (response.passage) {
          localStorage.setItem(PASSAGE_KEY, response.passage);
        }
        this.cleared.emit();
      },
      error: (err: HttpErrorResponse) => {
        this.submitting = false;
        this.errorKey = err.status === 0 ? 'wall.unreachable' : 'wall.badPassword';
      },
    });
  }

  private readPassage(): string {
    if (typeof localStorage === 'undefined') {
      return '';
    }
    return localStorage.getItem(PASSAGE_KEY) || '';
  }

  private clearPassage(): void {
    if (typeof localStorage === 'undefined') {
      return;
    }
    localStorage.removeItem(PASSAGE_KEY);
  }
}
