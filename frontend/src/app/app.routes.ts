import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/home/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'studio',
    loadComponent: () =>
      import('./features/studio/studio.component').then((m) => m.StudioComponent),
  },
  {
    path: 'tool',
    loadComponent: () =>
      import('./features/tool/tool.component').then((m) => m.ToolComponent),
  },
  {
    path: 'empresa',
    loadComponent: () =>
      import('./features/company/company.component').then((m) => m.CompanyComponent),
  },
  { path: '**', redirectTo: '' },
];
