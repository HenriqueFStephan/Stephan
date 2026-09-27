import {
  blocksFromEditor,
  hasComposerContent,
  insertImageChip,
  parseDataUrl,
  STUDIO_CHIP_ATTR,
  toApiBlocks,
} from './studio-blocks';

function editorWith(html: string): HTMLElement {
  const root = document.createElement('div');
  root.innerHTML = html;
  return root;
}

describe('studio-blocks', () => {
  it('parses data URLs', () => {
    const parsed = parseDataUrl('data:image/png;base64,abc123');
    expect(parsed.mime).toBe('image/png');
    expect(parsed.base64).toBe('abc123');
  });

  it('keeps text and snips in document order', () => {
    const root = editorWith(
      `Move the header<img ${STUDIO_CHIP_ATTR}="1" alt="snip 1" src="data:image/jpeg;base64,AAA" />Gold CTA`,
    );
    const blocks = blocksFromEditor(root);
    expect(blocks.length).toBe(3);
    expect(blocks[0]).toEqual({ type: 'text', text: 'Move the header' });
    expect(blocks[1]).toEqual({
      type: 'image',
      name: 'snip 1',
      mime: 'image/jpeg',
      dataUrl: 'data:image/jpeg;base64,AAA',
    });
    expect(blocks[2]).toEqual({ type: 'text', text: 'Gold CTA' });
    expect(hasComposerContent(blocks)).toBeTrue();
    expect(toApiBlocks(blocks)[1].data_base64).toBe('AAA');
  });

  it('inserts a chip at the end when the caret is outside the editor', () => {
    const editor = document.createElement('div');
    document.body.appendChild(editor);
    insertImageChip(editor, 'data:image/png;base64,QQ==', 'upload');
    const chip = editor.querySelector(`img[${STUDIO_CHIP_ATTR}]`) as HTMLImageElement | null;
    expect(chip?.alt).toBe('upload');
    expect(chip?.src).toContain('QQ==');
    editor.remove();
  });

  it('inserts a chip where the caret was, not at the start', () => {
    const editor = document.createElement('div');
    editor.appendChild(document.createTextNode('Hello world'));
    document.body.appendChild(editor);
    const text = editor.firstChild as Text;
    const range = document.createRange();
    range.setStart(text, 5);
    range.collapse(true);
    insertImageChip(editor, 'data:image/png;base64,QQ==', 'mid', range);
    const blocks = blocksFromEditor(editor);
    expect(blocks.map((block) => (block.type === 'text' ? block.text : block.name))).toEqual([
      'Hello',
      'mid',
      'world',
    ]);
    editor.remove();
  });
});
