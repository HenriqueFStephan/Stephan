import { compressCanvas, cropCanvas } from './snip-capture';

describe('snip-capture', () => {
  it('crops a region using the iframe CSS pixel width as the scale base', () => {
    const source = document.createElement('canvas');
    source.width = 200;
    source.height = 100;
    const ctx = source.getContext('2d')!;
    ctx.fillStyle = '#ff0000';
    ctx.fillRect(0, 0, 200, 100);
    ctx.fillStyle = '#00ff00';
    ctx.fillRect(40, 20, 20, 10);

    const cropped = cropCanvas(source, { x: 20, y: 10, width: 10, height: 5 }, 100);
    expect(cropped.width).toBe(20);
    expect(cropped.height).toBe(10);
  });

  it('compresses oversized canvases down to the max width', () => {
    const source = document.createElement('canvas');
    source.width = 3200;
    source.height = 1600;
    const dataUrl = compressCanvas(source, 1600, 0.8);
    expect(dataUrl.startsWith('data:image/jpeg')).toBeTrue();
  });
});
