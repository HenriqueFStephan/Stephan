/**
 * Ordered text/image blocks for the studio composer (mirrors a GitHub issue body).
 */

export const STUDIO_CHIP_ATTR = 'data-studio-snip';

export interface StudioTextBlock {
  type: 'text';
  text: string;
}

export interface StudioImageBlock {
  type: 'image';
  name: string;
  mime: string;
  dataUrl: string;
}

export type StudioComposerBlock = StudioTextBlock | StudioImageBlock;

export interface StudioApiBlock {
  type: 'text' | 'image';
  text?: string;
  name?: string;
  mime?: string;
  data_base64?: string;
}

export function parseDataUrl(dataUrl: string): { mime: string; base64: string } {
  const match = /^data:([^;,]+)(?:;charset=[^;,]+)?;base64,([\s\S]+)$/i.exec(dataUrl.trim());
  if (!match) {
    throw new Error('Invalid image data');
  }
  return { mime: match[1].toLowerCase(), base64: match[2].replace(/\s/g, '') };
}

export function blocksFromEditor(root: HTMLElement): StudioComposerBlock[] {
  const blocks: StudioComposerBlock[] = [];
  let text = '';

  const flush = (): void => {
    const cleaned = text.replace(/\u00a0/g, ' ').replace(/[ \t]+\n/g, '\n').trim();
    if (cleaned) {
      blocks.push({ type: 'text', text: cleaned });
    }
    text = '';
  };

  const walk = (node: Node): void => {
    if (node.nodeType === Node.TEXT_NODE) {
      text += node.textContent ?? '';
      return;
    }
    if (!(node instanceof HTMLElement)) {
      return;
    }
    if (node.matches(`img[${STUDIO_CHIP_ATTR}]`)) {
      flush();
      const dataUrl = node.getAttribute('src') || '';
      const name = (node.getAttribute('alt') || 'snip').trim() || 'snip';
      try {
        const { mime } = parseDataUrl(dataUrl);
        blocks.push({ type: 'image', name, mime, dataUrl });
      } catch {
        // Skip chips that lost their data URL.
      }
      return;
    }
    if (node.tagName === 'BR') {
      text += '\n';
      return;
    }
    const blockTag = ['DIV', 'P', 'LI'].includes(node.tagName);
    if (blockTag && text && !text.endsWith('\n')) {
      text += '\n';
    }
    node.childNodes.forEach(walk);
    if (blockTag && !text.endsWith('\n')) {
      text += '\n';
    }
  };

  root.childNodes.forEach(walk);
  flush();
  return blocks;
}

export function toApiBlocks(blocks: StudioComposerBlock[]): StudioApiBlock[] {
  return blocks.map((block) => {
    if (block.type === 'text') {
      return { type: 'text', text: block.text };
    }
    const parsed = parseDataUrl(block.dataUrl);
    return {
      type: 'image',
      name: block.name,
      mime: parsed.mime,
      data_base64: parsed.base64,
    };
  });
}

export function insertImageChip(editor: HTMLElement, dataUrl: string, name: string): void {
  const img = document.createElement('img');
  img.setAttribute(STUDIO_CHIP_ATTR, '1');
  img.src = dataUrl;
  img.alt = name;
  img.className = 'studio-chip';
  img.contentEditable = 'false';
  img.draggable = false;

  const selection = window.getSelection();
  const anchor = selection?.anchorNode ?? null;
  if (selection && selection.rangeCount && anchor && editor.contains(anchor)) {
    const range = selection.getRangeAt(0);
    range.deleteContents();
    range.insertNode(img);
    range.setStartAfter(img);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
    return;
  }
  editor.appendChild(img);
}

export function hasComposerContent(blocks: StudioComposerBlock[]): boolean {
  return blocks.some(
    (block) =>
      (block.type === 'text' && block.text.trim().length > 0) ||
      (block.type === 'image' && block.dataUrl.length > 0),
  );
}
