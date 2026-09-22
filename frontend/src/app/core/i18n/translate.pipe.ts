import { Pipe, PipeTransform } from '@angular/core';

import { I18nService } from './i18n.service';
import { MsgKey } from './messages';

@Pipe({
  name: 't',
  standalone: true,
  pure: false,
})
export class TranslatePipe implements PipeTransform {
  constructor(private i18n: I18nService) {}

  transform(key: MsgKey | string, params?: Record<string, string | number>): string {
    return this.i18n.t(key, params);
  }
}
