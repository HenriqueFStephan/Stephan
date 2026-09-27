import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  AfterViewInit,
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/api.service';
import { StudioStatusResponse } from '../../core/models';
import { TranslatePipe } from '../../core/i18n';
import { captureIframeRegion, normalizeImageDataUrl, readFileAsDataUrl, SnipRect } from './snip-capture';
import {
  blocksFromEditor,
  caretInEditor,
  hasComposerContent,
  insertImageChip,
  StudioComposerBlock,
  toApiBlocks,
} from './studio-blocks';

const TOKEN_KEY = 'stephan-studio-token';
const MIN_SNIP = 8;

export function isLocalStudioHost(hostname: string): boolean {
  const host = hostname.replace(/^\[|\]$/g, '').toLowerCase();
  return host === 'localhost' || host === '127.0.0.1' || host === '::1';
}

@Component({
  selector: 'app-studio',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './studio.component.html',
  styleUrls: ['./studio.component.scss'],
})
export class StudioComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('siteFrame') siteFrame?: ElementRef<HTMLIFrameElement>;
  @ViewChild('composer') composer?: ElementRef<HTMLElement>;
  @ViewChild('panel') panelEl?: ElementRef<HTMLElement>;
  @ViewChild('fileInput') fileInput?: ElementRef<HTMLInputElement>;

  unlocked = false;
  unlocking = false;
  token = '';
  gateError = '';
  status: StudioStatusResponse | null = null;

  snipping = false;
  snipHint = false;
  draft: SnipRect | null = null;
  private snipOrigin: { x: number; y: number } | null = null;

  panelLeft = 24;
  panelTop = 24;
  panelFromBottom = true;
  private drag: { offsetX: number; offsetY: number } | null = null;

  previewOpen = false;
  issueTitle = '';
  previewBlocks: StudioComposerBlock[] = [];
  submitting = false;
  submitError = '';
  issueUrl = '';
  sendMessage = '';
  sent = false;
  snipCount = 0;
  private savedCaret: Range | null = null;

  constructor(private api: ApiService) {}

  get needsGithubToken(): boolean {
    return (
      isLocalStudioHost(window.location.hostname) &&
      (this.status?.missing ?? []).includes('GITHUB_STUDIO_TOKEN')
    );
  }

  ngOnInit(): void {
    if (typeof window !== 'undefined' && window.self !== window.top) {
      window.location.replace('/');
      return;
    }
    this.api.getStudioStatus().subscribe({
      next: (status) => (this.status = status),
      error: () => (this.status = { configured: false, missing: [] }),
    });
    if (isLocalStudioHost(window.location.hostname)) {
      this.unlocked = true;
      return;
    }
    const stored = sessionStorage.getItem(TOKEN_KEY) || '';
    if (stored) {
      this.token = stored;
      this.unlock(stored);
    }
  }

  ngAfterViewInit(): void {
    this.placePanelDefault();
  }

  ngOnDestroy(): void {
    this.drag = null;
    this.snipOrigin = null;
  }

  unlock(token = this.token): void {
    const value = token.trim();
    if (!value || this.unlocking) {
      return;
    }
    this.unlocking = true;
    this.gateError = '';
    this.api.unlockStudio(value).subscribe({
      next: () => {
        sessionStorage.setItem(TOKEN_KEY, value);
        this.token = value;
        this.unlocked = true;
        this.unlocking = false;
      },
      error: (err: HttpErrorResponse) => {
        sessionStorage.removeItem(TOKEN_KEY);
        this.unlocked = false;
        this.unlocking = false;
        this.gateError =
          err.status === 503 ? 'studio.notConfigured' : 'studio.badToken';
      },
    });
  }

  rememberCaret(): void {
    const editor = this.composer?.nativeElement;
    if (!editor || document.activeElement !== editor) {
      return;
    }
    const caret = caretInEditor(editor);
    if (caret) {
      this.savedCaret = caret;
    }
  }

  startSnip(): void {
    if (!this.unlocked) {
      return;
    }
    this.snipping = true;
    this.snipHint = true;
    this.draft = null;
    this.snipOrigin = null;
  }

  cancelSnip(): void {
    this.snipping = false;
    this.snipHint = false;
    this.draft = null;
    this.snipOrigin = null;
  }

  onSnipPointerDown(event: PointerEvent): void {
    if (!this.snipping) {
      return;
    }
    (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
    const point = this.pointInTarget(event);
    this.snipOrigin = point;
    this.draft = { x: point.x, y: point.y, width: 0, height: 0 };
  }

  onSnipPointerMove(event: PointerEvent): void {
    if (!this.snipOrigin) {
      return;
    }
    const point = this.pointInTarget(event);
    const x = Math.min(this.snipOrigin.x, point.x);
    const y = Math.min(this.snipOrigin.y, point.y);
    this.draft = {
      x,
      y,
      width: Math.abs(point.x - this.snipOrigin.x),
      height: Math.abs(point.y - this.snipOrigin.y),
    };
  }

  async onSnipPointerUp(event: PointerEvent): Promise<void> {
    if (!this.snipping) {
      return;
    }
    const origin = this.snipOrigin;
    this.snipOrigin = null;
    const iframe = this.siteFrame?.nativeElement;
    const point = this.pointInTarget(event);
    if (!origin || !iframe) {
      this.cancelSnip();
      return;
    }
    let rect: SnipRect = {
      x: Math.min(origin.x, point.x),
      y: Math.min(origin.y, point.y),
      width: Math.abs(point.x - origin.x),
      height: Math.abs(point.y - origin.y),
    };
    if (rect.width < MIN_SNIP || rect.height < MIN_SNIP) {
      rect = { x: 0, y: 0, width: iframe.clientWidth, height: iframe.clientHeight };
    }
    this.snipping = false;
    this.snipHint = false;
    this.draft = null;
    try {
      const dataUrl = await captureIframeRegion(iframe, rect);
      this.snipCount += 1;
      this.insertImage(dataUrl, `snip-${this.snipCount}`);
    } catch (err) {
      console.error(err);
      this.submitError = 'studio.snipFailed';
    }
  }

  openFiles(): void {
    this.fileInput?.nativeElement.click();
  }

  async onFiles(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files || []);
    input.value = '';
    for (const file of files) {
      if (!file.type.startsWith('image/')) {
        continue;
      }
      const raw = await readFileAsDataUrl(file);
      const dataUrl = await normalizeImageDataUrl(raw);
      this.snipCount += 1;
      this.insertImage(dataUrl, file.name.replace(/\.[^.]+$/, '') || `upload-${this.snipCount}`);
    }
  }

  async onEditorPaste(event: ClipboardEvent): Promise<void> {
    this.rememberCaret();
    const items = Array.from(event.clipboardData?.items || []);
    const image = items.find((item) => item.type.startsWith('image/'));
    if (!image) {
      return;
    }
    event.preventDefault();
    const file = image.getAsFile();
    if (!file) {
      return;
    }
    const raw = await readFileAsDataUrl(file);
    const dataUrl = await normalizeImageDataUrl(raw);
    this.snipCount += 1;
    this.insertImage(dataUrl, `paste-${this.snipCount}`);
  }

  clearComposer(): void {
    const editor = this.composer?.nativeElement;
    if (editor) {
      editor.innerHTML = '';
    }
    this.snipCount = 0;
    this.submitError = '';
    this.issueUrl = '';
  }

  openPreview(): void {
    const editor = this.composer?.nativeElement;
    if (!editor) {
      return;
    }
    const blocks = blocksFromEditor(editor);
    if (!hasComposerContent(blocks)) {
      this.submitError = 'studio.emptyIssue';
      return;
    }
    this.previewBlocks = blocks;
    this.issueTitle = '';
    this.submitError = '';
    this.issueUrl = '';
    this.sendMessage = '';
    this.sent = false;
    this.previewOpen = true;
  }

  closePreview(): void {
    if (this.submitting) {
      return;
    }
    this.previewOpen = false;
  }

  sendIssue(): void {
    if (!this.issueTitle.trim() || this.submitting) {
      return;
    }
    this.submitting = true;
    this.submitError = '';
    this.api
      .submitStudioIssue(this.token, {
        title: this.issueTitle.trim(),
        blocks: toApiBlocks(this.previewBlocks),
      })
      .subscribe({
        next: (res) => {
          this.submitting = false;
          this.clearComposer();
          this.sent = true;
          this.issueUrl = res.issue_url || '';
          this.sendMessage = res.message || '';
        },
        error: (err: HttpErrorResponse) => {
          this.submitting = false;
          this.submitError =
            err.status === 401
              ? 'studio.badToken'
              : err.status === 503
                ? 'studio.notConfigured'
                : 'studio.sendFailed';
        },
      });
  }

  startDrag(event: PointerEvent): void {
    if ((event.target as HTMLElement).closest('button, a, input')) {
      return;
    }
    const panel = this.panelEl?.nativeElement;
    if (!panel) {
      return;
    }
    const box = panel.getBoundingClientRect();
    if (this.panelFromBottom) {
      this.panelTop = box.top;
      this.panelFromBottom = false;
    }
    this.drag = {
      offsetX: event.clientX - box.left,
      offsetY: event.clientY - box.top,
    };
    panel.setPointerCapture?.(event.pointerId);
    event.preventDefault();
  }

  onDragMove(event: PointerEvent): void {
    if (!this.drag) {
      return;
    }
    const panel = this.panelEl?.nativeElement;
    const width = panel?.offsetWidth ?? 320;
    const height = panel?.offsetHeight ?? 200;
    const maxLeft = Math.max(8, window.innerWidth - width - 8);
    const maxTop = Math.max(8, window.innerHeight - height - 8);
    this.panelLeft = Math.min(maxLeft, Math.max(8, event.clientX - this.drag.offsetX));
    this.panelTop = Math.min(maxTop, Math.max(8, event.clientY - this.drag.offsetY));
  }

  endDrag(): void {
    this.drag = null;
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.snipping) {
      this.cancelSnip();
      return;
    }
    if (this.previewOpen) {
      this.closePreview();
    }
  }

  trackPreview(_index: number, block: StudioComposerBlock): string {
    return block.type === 'text' ? `t:${block.text.slice(0, 24)}` : block.dataUrl.slice(-24);
  }

  private insertImage(dataUrl: string, name: string): void {
    const editor = this.composer?.nativeElement;
    if (!editor) {
      return;
    }
    insertImageChip(editor, dataUrl, name, this.savedCaret);
    const placed = caretInEditor(editor);
    if (placed) {
      this.savedCaret = placed;
    }
    editor.focus();
  }

  private placePanelDefault(): void {
    this.panelLeft = 24;
    this.panelFromBottom = true;
    this.panelTop = 24;
  }

  private pointInTarget(event: PointerEvent): { x: number; y: number } {
    const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
    return { x: event.clientX - box.left, y: event.clientY - box.top };
  }
}
