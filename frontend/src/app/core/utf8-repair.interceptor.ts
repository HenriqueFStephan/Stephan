import { HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { map } from 'rxjs/operators';

import { repairMojibake } from './utf8-repair';

/** Decode Portuguese (and other UTF-8) that arrived as Windows-1252 mojibake. */
export const utf8RepairInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    map((event) => {
      if (!(event instanceof HttpResponse) || event.body == null) {
        return event;
      }
      if (event.body instanceof ArrayBuffer || event.body instanceof Blob) {
        return event;
      }
      return event.clone({ body: repairMojibake(event.body) });
    }),
  );
};
