/** Capture a region of the same-origin site replica (iframe) as a JPEG data URL. */

export interface SnipRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function cropCanvas(
  source: HTMLCanvasElement,
  rect: SnipRect,
  sourceWidth: number,
): HTMLCanvasElement {
  const scale = source.width / Math.max(1, sourceWidth);
  const sx = Math.max(0, Math.round(rect.x * scale));
  const sy = Math.max(0, Math.round(rect.y * scale));
  const sw = Math.max(1, Math.round(rect.width * scale));
  const sh = Math.max(1, Math.round(rect.height * scale));
  const out = document.createElement('canvas');
  out.width = sw;
  out.height = sh;
  const ctx = out.getContext('2d');
  if (!ctx) {
    throw new Error('Could not crop snip');
  }
  ctx.drawImage(source, sx, sy, sw, sh, 0, 0, sw, sh);
  return out;
}

export function compressCanvas(
  canvas: HTMLCanvasElement,
  maxWidth = 1600,
  quality = 0.82,
): string {
  const ratio = canvas.width > maxWidth ? maxWidth / canvas.width : 1;
  const out = document.createElement('canvas');
  out.width = Math.max(1, Math.round(canvas.width * ratio));
  out.height = Math.max(1, Math.round(canvas.height * ratio));
  const ctx = out.getContext('2d');
  if (!ctx) {
    return canvas.toDataURL('image/jpeg', quality);
  }
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, out.width, out.height);
  ctx.drawImage(canvas, 0, 0, out.width, out.height);
  return out.toDataURL('image/jpeg', quality);
}

export async function captureIframeRegion(
  iframe: HTMLIFrameElement,
  rect: SnipRect,
): Promise<string> {
  const doc = iframe.contentDocument;
  const win = iframe.contentWindow;
  if (!doc || !win) {
    throw new Error('Site replica is not ready');
  }
  const html2canvas = (await import('html2canvas')).default;
  const width = iframe.clientWidth;
  const height = iframe.clientHeight;
  const full = await html2canvas(doc.documentElement, {
    x: win.scrollX,
    y: win.scrollY,
    width,
    height,
    windowWidth: width,
    windowHeight: height,
    scrollX: -win.scrollX,
    scrollY: -win.scrollY,
    scale: Math.min(2, window.devicePixelRatio || 1),
    useCORS: true,
    logging: false,
    backgroundColor: '#f8faf7',
  });
  const cropped = cropCanvas(full, rect, width);
  return compressCanvas(cropped);
}

export function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error ?? new Error('Could not read file'));
    reader.readAsDataURL(file);
  });
}

export async function normalizeImageDataUrl(dataUrl: string): Promise<string> {
  const image = new Image();
  image.src = dataUrl;
  await image.decode();
  const canvas = document.createElement('canvas');
  canvas.width = image.naturalWidth || image.width;
  canvas.height = image.naturalHeight || image.height;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    return dataUrl;
  }
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(image, 0, 0);
  return compressCanvas(canvas);
}
